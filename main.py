#!/usr/bin/env python3
"""
main.py — Portfolio Intelligence Digest orchestrator.
Runs daily at 8:15 AM ET via scheduled task.
Skips weekends and US market holidays automatically.
"""
import argparse
import logging
import sys
from datetime import datetime, date

import pandas_market_calendars as mcal
import pytz

from config import ACCOUNTS, ALL_TICKERS, GEMINI_API_KEY, GMAIL_APP_PASSWORD, RECIPIENT_EMAIL
from fetcher import get_market_data, get_commodity_data, get_sector_data, get_macro_news, fetch_all_ticker_data
from synthesizer import synthesize_account, synthesize_macro
from renderer import render_email
from sender import send_email

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("digest.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)
ET     = pytz.timezone("America/New_York")


# ── Guards ────────────────────────────────────────────────────────────────────

def _is_market_day(today: date) -> bool:
    """Return True if today is a NYSE trading day."""
    try:
        nyse     = mcal.get_calendar("NYSE")
        schedule = nyse.schedule(
            start_date=today.strftime("%Y-%m-%d"),
            end_date=today.strftime("%Y-%m-%d"),
        )
        return not schedule.empty
    except Exception as e:
        logger.warning(f"Market calendar check failed: {e}. Assuming market day.")
        return today.weekday() < 5  # fallback: Mon-Fri


def _validate_config() -> bool:
    """Fail fast if required credentials are missing."""
    ok = True
    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY is not set in .env")
        ok = False
    if not GMAIL_APP_PASSWORD:
        logger.error("GMAIL_APP_PASSWORD is not set in .env")
        ok = False
    return ok


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true", help="Bypass weekend/holiday check for testing")
    args = parser.parse_args()

    now   = datetime.now(ET)
    today = now.date()

    logger.info("=" * 60)
    logger.info(f"Portfolio Digest starting — {now.strftime('%Y-%m-%d %H:%M ET')}")
    logger.info("=" * 60)

    # Guard: credentials
    if not _validate_config():
        logger.error("Aborting — fix .env and retry.")
        sys.exit(1)

    # Guard: market day (skipped when --test flag is used)
    if not args.test and not _is_market_day(today):
        logger.info(f"{today} is not a trading day — skipping digest. Have a great day!")
        sys.exit(0)
    elif args.test:
        logger.info("--test flag active: bypassing market day check")

    # ── Step 1: Market, commodity & sector data ───────────────────────────────
    logger.info("Step 1/5 — Fetching market indices, commodities & sector data...")
    market_data    = get_market_data()
    commodity_data = get_commodity_data()
    sector_data    = get_sector_data()
    logger.info(f"  Indices: {len(market_data)} | Commodities: {len(commodity_data)} | Sectors: {len(sector_data)}")

    # ── Step 2: Macro news ────────────────────────────────────────────────────
    logger.info("Step 2/5 — Fetching macro news from RSS feeds...")
    macro_news = get_macro_news()
    logger.info(f"  {len(macro_news)} macro headlines collected")

    # ── Step 3: All ticker data + per-ticker news ─────────────────────────────
    logger.info(f"Step 3/5 — Fetching data for {len(ALL_TICKERS)} portfolio tickers...")
    ticker_data = fetch_all_ticker_data()
    with_news   = sum(1 for d in ticker_data.values() if d.get("news"))
    logger.info(f"  {len(ticker_data)} tickers with price data | {with_news} with recent news")

    # ── Step 4: AI synthesis ──────────────────────────────────────────────────
    logger.info("Step 4/5 — AI synthesis (Gemini 2.5 Flash)...")

    # Macro synthesis
    logger.info("  [Macro overview + outlook]")
    macro_synthesis = synthesize_macro(market_data, sector_data, macro_news)

    # Per-account synthesis (3 calls instead of ~33)
    account_syntheses: dict = {}
    for i, (acct_name, tickers) in enumerate(ACCOUNTS.items(), 1):
        news_count = sum(len(ticker_data.get(t, {}).get("news", [])) for t in tickers)
        logger.info(f"  [{i}/{len(ACCOUNTS)}] {acct_name} — {len(tickers)} holdings, {news_count} articles")
        account_syntheses[acct_name] = synthesize_account(acct_name, tickers, ticker_data)

    logger.info(f"  AI synthesis complete — {1 + len(ACCOUNTS)} total calls")

    # ── Step 5: Render + send ─────────────────────────────────────────────────
    logger.info("Step 5/5 — Rendering HTML and sending email...")
    html    = render_email(market_data, commodity_data, sector_data, macro_synthesis, account_syntheses, ticker_data)
    subject = f"Portfolio Digest — {now.strftime('%b %d, %Y')} | Pre-Market Brief"

    success = send_email(subject, html)

    if success:
        logger.info(f"Email sent to {RECIPIENT_EMAIL}")
        logger.info("=" * 60)
        logger.info("DONE - SUCCESS")
        logger.info("=" * 60)
    else:
        logger.error("Email send FAILED — check logs above for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
