import os
from dotenv import load_dotenv

load_dotenv()

# ── Portfolio ─────────────────────────────────────────────────────────────────
ACCOUNTS = {
    "Brokerage": ["GRAB", "KTOS", "ONDS", "NBIS", "XLE", "NU", "XLU"],
    "HSA": ["AMZN", "META", "MSFT", "VOO", "PPA", "IAUM", "XLU", "XLV"],
    "Roth IRA": [
        "CEG", "SLV", "COPX", "PLTR", "IAUM", "VST", "TSM", "EQIX",
        "GOOG", "NVDA", "ABBV", "VRT", "NEE", "MSFT", "NOC", "PANW",
        "AVAV", "TEM", "RKLB", "AVGO", "SOFI", "SHLD", "REMX", "CCJ",
        "NLR", "UNH", "VOO", "AVUV", "QQQM",
    ],
}
ALL_TICKERS = sorted(set(t for tickers in ACCOUNTS.values() for t in tickers))

# ── Market Indices ────────────────────────────────────────────────────────────
INDICES = {
    "S&P 500":   "^GSPC",
    "NASDAQ":    "^IXIC",
    "Dow Jones": "^DJI",
    "VIX":       "^VIX",
    "10Y Yield": "^TNX",
}

# ── Commodities ──────────────────────────────────────────────────────────────
COMMODITIES = {
    "Gold":   "GC=F",
    "Silver": "SI=F",
    "Copper": "HG=F",
}

# ── Sector ETFs ───────────────────────────────────────────────────────────────
SECTORS = {
    "Technology":       "XLK",
    "Energy":           "XLE",
    "Utilities":        "XLU",
    "Healthcare":       "XLV",
    "Financials":       "XLF",
    "Industrials":      "XLI",
    "Materials":        "XLB",
    "Comm. Services":   "XLC",
    "Consumer Disc.":   "XLY",
    "Consumer Staples": "XLP",
    "Real Estate":      "XLRE",
    "Defense":          "ITA",
}

# ── Credentials ───────────────────────────────────────────────────────────────
GEMINI_API_KEY     = os.getenv("GEMINI_API_KEY", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
SENDER_EMAIL       = "your_email@example.com"
RECIPIENT_EMAIL    = "your_email@example.com"

# ── AI ────────────────────────────────────────────────────────────────────────
GEMINI_MODEL  = "gemini-2.5-flash"
AI_CALL_DELAY = 5   # seconds between calls (free tier: 15 RPM)

# ── News ──────────────────────────────────────────────────────────────────────
NEWS_MAX_AGE_DAYS   = 3
NEWS_MAX_PER_TICKER = 8

# ── Macro RSS Feeds ───────────────────────────────────────────────────────────
MACRO_RSS_FEEDS = [
    "https://feeds.reuters.com/reuters/businessNews",
    "https://feeds.reuters.com/reuters/topNews",
    "https://www.cnbc.com/id/20910258/device/rss/rss.html",   # Economy
    "https://www.cnbc.com/id/100003114/device/rss/rss.html",  # Markets
    "https://feeds.content.dowjones.io/public/rss/mw_realtimeheadlines",
    "https://www.federalreserve.gov/feeds/press_all.xml",
    "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
]
