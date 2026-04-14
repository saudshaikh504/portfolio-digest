"""
synthesizer.py — Gemini 2.5 Flash AI synthesis for account-level and macro analysis.
Free tier: 1,500 requests/day, 15 RPM.  Each run uses ~4 calls (1 macro + 3 accounts).
"""
import time
import logging

from google import genai

from config import GEMINI_API_KEY, GEMINI_MODEL, AI_CALL_DELAY

logger = logging.getLogger(__name__)

_client = genai.Client(api_key=GEMINI_API_KEY)


# ── Core API call ─────────────────────────────────────────────────────────────

def _call_gemini(prompt: str, retries: int = 2) -> str:
    for attempt in range(retries + 1):
        try:
            response = _client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
            )
            return response.text.strip()
        except Exception as e:
            logger.warning(f"Gemini call failed (attempt {attempt + 1}/{retries + 1}): {e}")
            if attempt < retries:
                time.sleep(15)
    return ""


# ── Account-level synthesis ──────────────────────────────────────────────────

def synthesize_account(account_name: str, account_tickers: list, ticker_data: dict) -> dict:
    """
    Returns:
        overview        — 3-5 sentence overview of key movements and themes
        high_conviction — list of bullet strings (e.g. "KTOS BULLISH: reason...")
        sentiment       — "bullish" | "bearish" | "neutral"
    """
    holdings_info = []
    all_headlines = []
    for ticker in account_tickers:
        if ticker not in ticker_data:
            continue
        d = ticker_data[ticker]
        holdings_info.append(
            f"  {ticker} ({d['name']}): ${d['price']:,.2f} | Day: {d['change_pct']:+.2f}% | 5D: {d['week_change_pct']:+.2f}%"
        )
        for article in d.get("news", []):
            all_headlines.append(f"  - [{article['source']}] {ticker}: {article['title']}")

    holdings_block  = "\n".join(holdings_info)
    headlines_block = "\n".join(all_headlines[:30])

    prompt = f"""You are a professional financial analyst writing a pre-market morning briefing for a sophisticated individual investor.

Account: {account_name}
Holdings:
{holdings_block}

Recent News Headlines (past 3 days):
{headlines_block if all_headlines else "No significant news for any holdings in this account."}

Respond in EXACTLY this structured format — no extra text, no markdown, no headers:

OVERVIEW: [3-5 concise sentences covering the most material developments across this account. Focus on themes and trends, not individual price moves. Be specific — name actual events, catalysts, or risks. If nothing significant, say so briefly.]
HIGH_CONVICTION: [List 2-4 high-conviction observations using * bullets. Format each as: * TICKER DIRECTION: reason. DIRECTION must be BULLISH, BEARISH, or NEUTRAL. Only include holdings with a clear, actionable thesis based on recent news or price action. If none stand out, write: * No high-conviction signals this session.]
SENTIMENT: [BULLISH or BEARISH or NEUTRAL — overall account bias for today]"""

    time.sleep(AI_CALL_DELAY)
    raw = _call_gemini(prompt)

    result = {
        "overview":        "",
        "high_conviction": [],
        "sentiment":       "neutral",
    }

    current_key      = None
    conviction_lines = []

    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("OVERVIEW:"):
            current_key = "overview"
            result["overview"] = line[len("OVERVIEW:"):].strip()
        elif line.startswith("HIGH_CONVICTION:"):
            current_key = "high_conviction"
            first = line[len("HIGH_CONVICTION:"):].strip()
            if first.startswith("*"):
                conviction_lines.append(first[1:].strip())
        elif line.startswith("SENTIMENT:"):
            current_key = "sentiment"
            val = line[len("SENTIMENT:"):].strip().upper()
            if val in ("BULLISH", "BEARISH", "NEUTRAL"):
                result["sentiment"] = val.lower()
        elif current_key == "high_conviction" and line.startswith("*"):
            conviction_lines.append(line[1:].strip())
        elif current_key == "overview" and not any(
            line.startswith(k) for k in ("HIGH_CONVICTION:", "SENTIMENT:", "*")
        ):
            result["overview"] += " " + line

    result["high_conviction"] = conviction_lines
    result["overview"]        = result["overview"].strip()

    return result


# ── Macro synthesis ───────────────────────────────────────────────────────────

def synthesize_macro(
    market_data: dict,
    sector_data: dict,
    macro_news: list[dict],
) -> dict:
    """
    Returns:
        market_overview — 2-3 sentence market tone/driver summary
        key_events      — list of bullet strings for the week's major events
        macro_outlook   — 2-3 sentence macro environment summary
    """
    mkt_lines = "\n".join(
        f"  {name}: {d['price']:,}  ({d['change_pct']:+.2f}%)"
        for name, d in market_data.items()
    )

    sector_sorted = sorted(sector_data.items(), key=lambda x: x[1]["change_pct"], reverse=True)
    sector_lines  = "\n".join(
        f"  {name} ({d['symbol']}): {d['change_pct']:+.2f}%"
        for name, d in sector_sorted
    )

    headlines = "\n".join(
        f"- [{item['source']}] {item['title']}"
        for item in macro_news[:35]
    )

    prompt = f"""You are a senior macro strategist writing the market overview section of a professional morning briefing.

Previous Session — Market Close:
{mkt_lines}

Sector Performance (previous session):
{sector_lines}

Recent Macro & Market News:
{headlines}

Respond in EXACTLY this structured format — no extra text, no markdown, no headers:

MARKET_OVERVIEW: [2-3 sentences on overall market tone, key drivers, and sentiment. Reference specific index levels or moves. Be direct and data-driven.]
KEY_EVENTS: [Bullet list using * of the 3-5 most important economic releases or market catalysts scheduled this week. Format each as: * Day: Event — brief impact note. If no major events are known, write: * No major scheduled economic releases this week.]
MACRO_OUTLOOK: [2-3 sentences on the broader macro environment: Federal Reserve policy stance, interest rate trajectory, inflation trends, and any geopolitical or economic risks that matter for equities.]"""

    time.sleep(AI_CALL_DELAY)
    raw = _call_gemini(prompt)

    result = {
        "market_overview": "",
        "key_events":      [],
        "macro_outlook":   "",
    }

    current_key     = None
    key_event_lines = []

    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("MARKET_OVERVIEW:"):
            current_key = "market_overview"
            result["market_overview"] = line[len("MARKET_OVERVIEW:"):].strip()
        elif line.startswith("KEY_EVENTS:"):
            current_key = "key_events"
            first = line[len("KEY_EVENTS:"):].strip()
            if first.startswith("*"):
                key_event_lines.append(first[1:].strip())
        elif line.startswith("MACRO_OUTLOOK:"):
            current_key = "macro_outlook"
            result["macro_outlook"] = line[len("MACRO_OUTLOOK:"):].strip()
        elif current_key == "key_events" and line.startswith("*"):
            key_event_lines.append(line[1:].strip())
        elif current_key == "market_overview" and not any(
            line.startswith(k) for k in ("KEY_EVENTS:", "MACRO_OUTLOOK:", "*")
        ):
            result["market_overview"] += " " + line
        elif current_key == "macro_outlook" and not line.startswith("*"):
            result["macro_outlook"] += " " + line

    result["key_events"]      = key_event_lines
    result["market_overview"] = result["market_overview"].strip()
    result["macro_outlook"]   = result["macro_outlook"].strip()

    return result
