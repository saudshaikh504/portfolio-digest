"""
fetcher.py — Market data, news, and ticker metadata retrieval.
Uses yfinance (batch downloads) + Yahoo Finance RSS + multi-source macro RSS.
"""
import time
import logging
from datetime import datetime, timedelta, timezone, date
from concurrent.futures import ThreadPoolExecutor, as_completed

import feedparser
import pandas as pd
import yfinance as yf
from bs4 import BeautifulSoup

from config import (
    ALL_TICKERS, INDICES, SECTORS, COMMODITIES, MACRO_RSS_FEEDS,
    NEWS_MAX_AGE_DAYS, NEWS_MAX_PER_TICKER,
)

logger = logging.getLogger(__name__)

# ── Internal helpers ──────────────────────────────────────────────────────────

def _is_recent(entry: dict) -> bool:
    """Return True if a feed entry falls within NEWS_MAX_AGE_DAYS."""
    try:
        pub = entry.get("published_parsed") or entry.get("updated_parsed")
        if not pub:
            return True
        pub_dt = datetime(*pub[:6], tzinfo=timezone.utc)
        cutoff = datetime.now(timezone.utc) - timedelta(days=NEWS_MAX_AGE_DAYS)
        return pub_dt >= cutoff
    except Exception:
        return True


def _extract_closes(raw: pd.DataFrame) -> pd.DataFrame:
    """Safely extract the Close column from a yf.download result."""
    if raw is None or raw.empty:
        return pd.DataFrame()
    if isinstance(raw.columns, pd.MultiIndex):
        try:
            return raw["Close"]
        except KeyError:
            return pd.DataFrame()
    return raw


def _parse_earnings_date(cal) -> str | None:
    """Parse the next upcoming earnings date from yf.Ticker.calendar."""
    try:
        if isinstance(cal, dict):
            dates = cal.get("Earnings Date", [])
        elif cal is not None and hasattr(cal, "loc"):
            try:
                dates = list(cal.loc["Earnings Date"])
            except Exception:
                return None
        else:
            return None

        for d in dates:
            try:
                if hasattr(d, "date"):
                    d = d.date()
                elif isinstance(d, str):
                    d = date.fromisoformat(d.split()[0])
                if d >= date.today():
                    return str(d)
            except Exception:
                continue
    except Exception:
        pass
    return None


# ── Market & Sector Data ──────────────────────────────────────────────────────

def get_market_data() -> dict:
    """Fetch previous-close data for the major market indices."""
    result = {}
    for name, sym in INDICES.items():
        try:
            hist = yf.Ticker(sym).history(period="2d")
            if hist.empty:
                continue
            price = float(hist["Close"].iloc[-1])
            prev  = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else price
            chg   = (price - prev) / prev * 100 if prev else 0
            result[name] = {
                "symbol":     sym,
                "price":      round(price, 4 if sym == "^TNX" else 2),
                "change_pct": round(chg, 2),
            }
        except Exception as e:
            logger.warning(f"Index {name}: {e}")
    return result


def get_commodity_data() -> dict:
    """Fetch previous-close data for gold, silver, copper futures."""
    result = {}
    for name, sym in COMMODITIES.items():
        try:
            hist = yf.Ticker(sym).history(period="2d")
            if hist.empty:
                continue
            price = float(hist["Close"].iloc[-1])
            prev  = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else price
            chg   = (price - prev) / prev * 100 if prev else 0
            result[name] = {
                "symbol":     sym,
                "price":      round(price, 2),
                "change_pct": round(chg, 2),
            }
        except Exception as e:
            logger.warning(f"Commodity {name}: {e}")
    return result


def get_sector_data() -> dict:
    """Fetch previous-close 1-day change for all sector ETFs."""
    symbols = list(SECTORS.values())
    result  = {}
    try:
        raw    = yf.download(symbols, period="2d", progress=False, auto_adjust=True, threads=True)
        closes = _extract_closes(raw)
        for name, sym in SECTORS.items():
            try:
                s = closes[sym].dropna()
                if len(s) < 2:
                    continue
                price = float(s.iloc[-1])
                prev  = float(s.iloc[-2])
                chg   = (price - prev) / prev * 100 if prev else 0
                result[name] = {
                    "symbol":     sym,
                    "price":      round(price, 2),
                    "change_pct": round(chg, 2),
                }
            except Exception as e:
                logger.debug(f"Sector {name}: {e}")
    except Exception as e:
        logger.warning(f"Sector batch download: {e}")
    return result


# ── Ticker Metadata ───────────────────────────────────────────────────────────

def _fetch_ticker_meta(ticker: str) -> tuple[str, dict]:
    """Fetch company name + next earnings date for a single ticker (runs in thread pool)."""
    meta = {"name": ticker, "earnings_date": None}
    try:
        t    = yf.Ticker(ticker)
        info = t.info
        meta["name"] = (
            info.get("shortName") or info.get("longName") or ticker
        )
        meta["earnings_date"] = _parse_earnings_date(t.calendar)
    except Exception as e:
        logger.debug(f"Meta {ticker}: {e}")
    return ticker, meta


# ── News ──────────────────────────────────────────────────────────────────────

def get_ticker_news(ticker: str) -> list[dict]:
    """Fetch recent headlines from Yahoo Finance RSS for a single ticker."""
    url      = (
        f"https://feeds.finance.yahoo.com/rss/2.0/headline"
        f"?s={ticker}&region=US&lang=en-US"
    )
    articles = []
    try:
        feed = feedparser.parse(url, request_headers={"User-Agent": "Mozilla/5.0"})
        for entry in feed.entries:
            if not _is_recent(entry):
                continue
            source   = entry.get("source", {})
            src_name = (
                source.get("title", "Yahoo Finance")
                if isinstance(source, dict) else "Yahoo Finance"
            )
            raw_summary = entry.get("summary", "")
            summary     = BeautifulSoup(raw_summary, "lxml").get_text()[:300].strip()
            articles.append({
                "title":     entry.get("title", "").strip(),
                "source":    src_name,
                "published": entry.get("published", ""),
                "summary":   summary,
                "url":       entry.get("link", ""),
            })
            if len(articles) >= NEWS_MAX_PER_TICKER:
                break
    except Exception as e:
        logger.debug(f"News RSS {ticker}: {e}")
    return articles


def get_macro_news() -> list[dict]:
    """Aggregate macro/market news from multiple RSS feeds."""
    articles = []
    seen     = set()
    for feed_url in MACRO_RSS_FEEDS:
        try:
            feed = feedparser.parse(
                feed_url,
                request_headers={"User-Agent": "Mozilla/5.0"},
            )
            for entry in feed.entries[:15]:
                if not _is_recent(entry):
                    continue
                title = entry.get("title", "").strip()
                if not title or title in seen:
                    continue
                seen.add(title)
                raw_summary = entry.get("summary", "")
                summary     = BeautifulSoup(raw_summary, "lxml").get_text()[:300].strip()
                articles.append({
                    "title":     title,
                    "source":    feed.feed.get("title", "News"),
                    "published": entry.get("published", ""),
                    "summary":   summary,
                    "url":       entry.get("link", ""),
                })
        except Exception as e:
            logger.debug(f"Macro RSS {feed_url}: {e}")
    return articles


# ── Main Fetch Orchestrator ───────────────────────────────────────────────────

def fetch_all_ticker_data() -> dict:
    """
    Returns a dict keyed by ticker symbol:
        {
          ticker, name, price, prev_close, change, change_pct,
          week_change_pct, pre_market_price, earnings_date, news: [...]
        }
    Only tickers with valid price data are included.
    """
    # 1. Batch price download (fast, single HTTP session)
    logger.info(f"Batch downloading prices for {len(ALL_TICKERS)} tickers...")
    try:
        raw    = yf.download(
            ALL_TICKERS, period="5d",
            progress=False, auto_adjust=True, threads=True,
        )
        closes = _extract_closes(raw)
    except Exception as e:
        logger.error(f"Batch price download failed: {e}")
        closes = pd.DataFrame()

    # 2. Parallel metadata fetch (company name + earnings) — 8 threads
    logger.info("Fetching ticker metadata in parallel...")
    meta_map: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(_fetch_ticker_meta, t): t for t in ALL_TICKERS}
        for fut in as_completed(futs, timeout=150):
            ticker = futs[fut]
            try:
                _, meta = fut.result()
                meta_map[ticker] = meta
            except Exception as e:
                logger.debug(f"Meta future {ticker}: {e}")
                meta_map[ticker] = {"name": ticker, "earnings_date": None}

    # 3. Build price records
    results: dict[str, dict] = {}
    for ticker in ALL_TICKERS:
        try:
            if ticker not in closes.columns:
                continue
            col = closes[ticker].dropna()
            if col.empty:
                continue
            price     = float(col.iloc[-1])
            prev      = float(col.iloc[-2]) if len(col) >= 2 else price
            week_open = float(col.iloc[0])
            chg       = price - prev
            chg_pct   = (chg / prev * 100) if prev else 0.0
            wchg_pct  = ((price - week_open) / week_open * 100) if week_open else 0.0

            # Pre-market price (best-effort)
            pre_price = None
            try:
                fi = yf.Ticker(ticker).fast_info
                pm = getattr(fi, "pre_market_price", None)
                if pm and float(pm) > 0:
                    pre_price = round(float(pm), 2)
            except Exception:
                pass

            m = meta_map.get(ticker, {})
            results[ticker] = {
                "ticker":           ticker,
                "name":             m.get("name", ticker),
                "price":            round(price, 2),
                "prev_close":       round(prev, 2),
                "change":           round(chg, 2),
                "change_pct":       round(chg_pct, 2),
                "week_change_pct":  round(wchg_pct, 2),
                "pre_market_price": pre_price,
                "earnings_date":    m.get("earnings_date"),
                "news":             [],
            }
        except Exception as e:
            logger.warning(f"Price parse {ticker}: {e}")

    # 4. News per ticker (sequential — Yahoo Finance is sensitive to bursts)
    logger.info(f"Fetching news for {len(results)} tickers...")
    for ticker in results:
        results[ticker]["news"] = get_ticker_news(ticker)
        time.sleep(0.4)

    return results
