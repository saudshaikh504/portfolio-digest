# Portfolio Tracker

A pre-market portfolio intelligence email delivered every weekday morning. Pulls live market data, commodity prices, sector performance, and per-holding news, then uses Gemini to write account-level commentary and a macro overview.

## What it does

- Fetches real-time data for configured holdings via yfinance (indices, commodities, sectors, individual tickers)
- Pulls macro news from RSS feeds and per-ticker news from Yahoo Finance
- Runs 4 Gemini calls: one macro overview and one per brokerage account
- Skips weekends and US market holidays automatically via NYSE calendar
- Renders a full HTML email and sends via Gmail SMTP
- Runs weekdays via GitHub Actions with DST-safe scheduling and a cache-based dedup guard

## Stack

- **Python** — yfinance, feedparser, google-genai, pandas-market-calendars, smtplib
- **Gemini 2.5 Flash** — macro synthesis and per-account commentary
- **Gmail SMTP** — delivery
- **GitHub Actions** — scheduled weekdays at 6 AM ET

## Setup

1. Clone the repo
2. Copy `.env.example` to `.env` and fill in your credentials:
   - `GEMINI_API_KEY` — free at [aistudio.google.com](https://aistudio.google.com/app/apikey)
   - `GMAIL_APP_PASSWORD` — a Gmail App Password (not your regular password)
3. Configure your holdings and accounts in `config.py`
4. Install dependencies: `pip install -r requirements.txt`
5. Run manually: `python main.py`
6. Use `python main.py --test` to bypass the market day check

To run on a schedule, add your credentials as GitHub Actions secrets and enable the included workflow.
