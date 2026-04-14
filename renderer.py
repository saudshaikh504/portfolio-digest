"""
renderer.py — Builds the full HTML email for the Portfolio Intelligence Digest.
Dark-theme, Bloomberg-inspired, fully inline-styled for Gmail compatibility.
Account-level summaries with high-conviction trend highlights.
Earnings calendar shows only holdings with earnings THIS calendar week.
"""
from datetime import datetime, date, timedelta
import pytz

from config import ACCOUNTS

ET = pytz.timezone("America/New_York")

# ── Color helpers ─────────────────────────────────────────────────────────────

SENTIMENT = {
    "bullish": {
        "color":  "#4ade80",
        "bg":     "#052e16",
        "border": "#166534",
        "text":   "#bbf7d0",
        "icon":   "▲",
        "label":  "BULLISH",
    },
    "bearish": {
        "color":  "#f87171",
        "bg":     "#2d0a0a",
        "border": "#7f1d1d",
        "text":   "#fecaca",
        "icon":   "▼",
        "label":  "BEARISH",
    },
    "neutral": {
        "color":  "#fbbf24",
        "bg":     "#1c1500",
        "border": "#78350f",
        "text":   "#fde68a",
        "icon":   "◆",
        "label":  "NEUTRAL",
    },
}

ACCOUNT_COLORS = {
    "Brokerage": "#60a5fa",
    "HSA":       "#34d399",
    "Roth IRA":  "#818cf8",
}


def _pct_color(val: float) -> str:
    if val > 0:  return "#4ade80"
    if val < 0:  return "#f87171"
    return "#94a3b8"


def _fmt_pct(val: float) -> str:
    icon = "▲" if val > 0 else ("▼" if val < 0 else "")
    return f"{icon} {abs(val):.2f}%"


def _fmt_price(val: float) -> str:
    return f"${val:,.2f}"


# ── Section builders ──────────────────────────────────────────────────────────

def _build_indices_row(market_data: dict) -> str:
    cells = ""
    for name, d in market_data.items():
        color = _pct_color(d["change_pct"])
        pct   = _fmt_pct(d["change_pct"])
        price = f"{d['price']:,}" if name in ("S&P 500", "Dow Jones", "NASDAQ") else str(d["price"])
        cells += f"""
      <td style="padding:14px 16px;text-align:center;border-right:1px solid #1e3a5f;vertical-align:middle;">
        <div style="font-size:10px;color:#64748b;letter-spacing:0.8px;text-transform:uppercase;font-weight:600;margin-bottom:4px;">{name}</div>
        <div style="font-size:16px;font-weight:700;color:#f1f5f9;">{price}</div>
        <div style="font-size:12px;font-weight:600;color:{color};margin-top:2px;">{pct}</div>
      </td>"""
    return cells


def _build_commodities_row(commodity_data: dict) -> str:
    if not commodity_data:
        return ""
    cells = ""
    for name, d in commodity_data.items():
        color = _pct_color(d["change_pct"])
        pct   = _fmt_pct(d["change_pct"])
        cells += f"""
      <td width="33%" style="padding:10px 16px;text-align:center;border-right:1px solid #1e3a5f;vertical-align:middle;">
        <div style="font-size:10px;color:#64748b;letter-spacing:0.8px;text-transform:uppercase;font-weight:600;margin-bottom:3px;">{name}</div>
        <div style="font-size:14px;font-weight:700;color:#f1f5f9;">{_fmt_price(d['price'])}</div>
        <div style="font-size:11px;font-weight:600;color:{color};margin-top:2px;">{pct}</div>
      </td>"""
    return cells


def _build_sector_rows(sector_data: dict) -> str:
    rows  = ""
    items = sorted(sector_data.items(), key=lambda x: x[1]["change_pct"], reverse=True)
    for i, (name, d) in enumerate(items):
        bg    = "#111827" if i % 2 == 0 else "#0f172a"
        color = _pct_color(d["change_pct"])
        bar_w = min(abs(d["change_pct"]) * 18, 100)
        bar_c = "#16a34a" if d["change_pct"] >= 0 else "#dc2626"
        rows += f"""
      <tr style="background:{bg};">
        <td style="padding:7px 14px;color:#cbd5e1;font-size:13px;white-space:nowrap;">{name}</td>
        <td style="padding:7px 8px;color:#475569;font-size:11px;">{d['symbol']}</td>
        <td style="padding:7px 14px;text-align:right;color:{color};font-weight:600;font-size:13px;white-space:nowrap;">{_fmt_pct(d['change_pct'])}</td>
        <td style="padding:7px 14px;width:90px;">
          <div style="background:#1e293b;border-radius:2px;height:5px;overflow:hidden;">
            <div style="width:{bar_w:.0f}%;background:{bar_c};border-radius:2px;height:5px;"></div>
          </div>
        </td>
      </tr>"""
    return rows


def _build_earnings_calendar(ticker_data: dict) -> str:
    """Show only portfolio holdings with earnings THIS calendar week (Mon-Fri)."""
    today  = date.today()
    monday = today - timedelta(days=today.weekday())
    friday = monday + timedelta(days=4)

    upcoming, seen = [], set()
    for ticker, d in ticker_data.items():
        ed = d.get("earnings_date")
        if ed and ticker not in seen:
            ed_date = date.fromisoformat(ed)
            if monday <= ed_date <= friday:
                seen.add(ticker)
                days_away = (ed_date - today).days
                upcoming.append((days_away, ticker, d["name"], ed))

    if not upcoming:
        return ""

    upcoming.sort()
    rows = ""
    for days, ticker, name, ed in upcoming:
        uc    = "#f59e0b" if days <= 2 else "#60a5fa"
        badge = "TODAY" if days == 0 else ("TOMORROW" if days == 1 else f"{ed}")
        rows += f"""
      <tr>
        <td style="padding:7px 14px;font-weight:700;color:#f1f5f9;font-size:13px;">{ticker}</td>
        <td style="padding:7px 8px;color:#94a3b8;font-size:12px;">{name}</td>
        <td style="padding:7px 14px;color:{uc};font-size:13px;white-space:nowrap;">{ed}</td>
        <td style="padding:7px 14px;">
          <span style="background:{uc}22;color:{uc};border:1px solid {uc}55;border-radius:4px;padding:2px 8px;font-size:10px;font-weight:700;">{badge}</span>
        </td>
      </tr>"""

    week_range = f"{monday.strftime('%b %d')} - {friday.strftime('%b %d')}"
    return f"""
  <div style="background:#0f172a;border:1px solid #1e293b;border-radius:10px;padding:20px 24px;margin-bottom:20px;">
    <div style="font-size:10px;font-weight:700;color:#f59e0b;letter-spacing:1px;text-transform:uppercase;margin-bottom:14px;">
      Earnings This Week ({week_range}) — Your Holdings
    </div>
    <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
      {rows}
    </table>
  </div>"""


def _build_holdings_grid(tickers: list, ticker_data: dict) -> str:
    """Compact grid of ticker badges showing day change."""
    badges = []
    for ticker in sorted(tickers):
        if ticker not in ticker_data:
            continue
        d     = ticker_data[ticker]
        color = _pct_color(d["change_pct"])
        icon  = "▲" if d["change_pct"] > 0 else ("▼" if d["change_pct"] < 0 else "")
        badges.append(
            f'<span style="display:inline-block;margin:3px 4px;padding:4px 10px;'
            f'background:#111827;border:1px solid #1e293b;border-radius:5px;'
            f'font-size:12px;">'
            f'<span style="color:#f1f5f9;font-weight:700;">{ticker}</span> '
            f'<span style="color:{color};font-weight:600;">{icon}{abs(d["change_pct"]):.2f}%</span>'
            f'</span>'
        )
    return "".join(badges)


def _build_conviction_items(high_conviction: list) -> str:
    """Render high conviction items as styled boxes."""
    if not high_conviction:
        return ""
    # Filter out "no signal" placeholders
    real = [c for c in high_conviction if "no high-conviction" not in c.lower()]
    if not real:
        return ""

    items = ""
    for item in real:
        upper = item.upper()
        if "BULLISH" in upper:
            color, bg, border = "#4ade80", "#052e16", "#166534"
        elif "BEARISH" in upper:
            color, bg, border = "#f87171", "#2d0a0a", "#7f1d1d"
        else:
            color, bg, border = "#fbbf24", "#1c1500", "#78350f"

        items += (
            f'<div style="background:{bg};border:1px solid {border};border-radius:6px;'
            f'padding:8px 12px;margin-bottom:6px;">'
            f'<div style="font-size:12px;color:{color};line-height:1.5;">{item}</div>'
            f'</div>'
        )

    return (
        f'<div style="margin-top:14px;">'
        f'<div style="font-size:10px;font-weight:700;color:#f59e0b;letter-spacing:1px;'
        f'text-transform:uppercase;margin-bottom:8px;">High Conviction</div>'
        f'{items}</div>'
    )


def _build_account_summary(
    account_name: str,
    tickers: list,
    ticker_data: dict,
    synthesis: dict,
) -> str:
    """Build a concise account-level section with holdings grid, AI overview, and conviction highlights."""
    accent = ACCOUNT_COLORS.get(account_name, "#60a5fa")

    valid   = [t for t in tickers if t in ticker_data]
    up_cnt  = sum(1 for t in valid if ticker_data[t]["change_pct"] > 0)
    dn_cnt  = sum(1 for t in valid if ticker_data[t]["change_pct"] < 0)

    sc = SENTIMENT[synthesis.get("sentiment", "neutral")]

    holdings_grid  = _build_holdings_grid(tickers, ticker_data)
    overview       = synthesis.get("overview", "")
    conviction_html = _build_conviction_items(synthesis.get("high_conviction", []))

    return f"""
  <div style="background:#0f172a;border:1px solid #1e293b;border-radius:10px;padding:20px 24px;margin-bottom:16px;">
    <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;margin-bottom:14px;">
      <tr>
        <td style="border-left:3px solid {accent};padding-left:12px;">
          <span style="font-size:13px;font-weight:800;color:{accent};letter-spacing:1.5px;text-transform:uppercase;">{account_name}</span>
          <span style="font-size:11px;color:#475569;margin-left:10px;">{len(valid)} holdings &middot; {up_cnt} up &middot; {dn_cnt} down</span>
        </td>
        <td style="text-align:right;">
          <span style="background:{sc['bg']};color:{sc['color']};border:1px solid {sc['border']};border-radius:4px;padding:3px 10px;font-size:10px;font-weight:700;letter-spacing:0.5px;">{sc['icon']} {sc['label']}</span>
        </td>
      </tr>
    </table>

    <div style="margin-bottom:12px;">{holdings_grid}</div>

    <p style="margin:0 0 4px 0;color:#cbd5e1;font-size:13px;line-height:1.7;">{overview}</p>

    {conviction_html}
  </div>"""


# ── Main render ───────────────────────────────────────────────────────────────

def render_email(
    market_data: dict,
    commodity_data: dict,
    sector_data: dict,
    macro_synthesis: dict,
    account_syntheses: dict,
    ticker_data: dict,
) -> str:
    now_et   = datetime.now(ET)
    date_str = now_et.strftime("%A, %B %d, %Y")
    time_str = now_et.strftime("%I:%M %p ET")

    indices_cells    = _build_indices_row(market_data)
    commodities_cells = _build_commodities_row(commodity_data)
    sector_rows      = _build_sector_rows(sector_data)
    earnings_cal     = _build_earnings_calendar(ticker_data)

    account_sections = ""
    for acct_name, tickers in ACCOUNTS.items():
        synth = account_syntheses.get(acct_name, {
            "overview": "", "high_conviction": [], "sentiment": "neutral",
        })
        account_sections += _build_account_summary(acct_name, tickers, ticker_data, synth)

    events_items = "".join(
        f'<li style="margin:7px 0;color:#cbd5e1;font-size:13px;line-height:1.6;">{ev}</li>'
        for ev in macro_synthesis.get("key_events", [])
    ) or '<li style="color:#475569;font-size:13px;">No major scheduled events identified this week.</li>'

    market_overview = macro_synthesis.get("market_overview", "")
    macro_outlook   = macro_synthesis.get("macro_outlook", "")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Portfolio Digest — {date_str}</title>
</head>
<body style="margin:0;padding:0;background-color:#060d18;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;">
<div style="max-width:700px;margin:0 auto;padding:16px;">

  <!-- HEADER -->
  <div style="background:linear-gradient(135deg,#0c2340 0%,#0f172a 60%,#0c1e3c 100%);border-radius:12px 12px 0 0;padding:28px 32px;border-bottom:2px solid #1e4a80;">
    <div style="font-size:10px;color:#3b82f6;letter-spacing:2.5px;text-transform:uppercase;font-weight:700;margin-bottom:6px;">Portfolio Intelligence Digest</div>
    <div style="font-size:26px;font-weight:800;color:#f8fafc;letter-spacing:-0.5px;">{date_str}</div>
    <div style="font-size:12px;color:#475569;margin-top:6px;">Pre-Market Edition &nbsp;&middot;&nbsp; Generated at {time_str} &nbsp;&middot;&nbsp; Prices reflect prior session close</div>
  </div>

  <!-- MARKET INDICES -->
  <div style="background:#0c1929;border-left:1px solid #1e293b;border-right:1px solid #1e293b;">
    <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
      <tr>{indices_cells}</tr>
    </table>
  </div>

  <!-- COMMODITIES -->
  <div style="background:#0c1929;border-left:1px solid #1e293b;border-right:1px solid #1e293b;border-top:1px solid #1e3a5f;">
    <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
      <tr>{commodities_cells}</tr>
    </table>
  </div>

  <!-- MARKET OVERVIEW -->
  <div style="background:#0f172a;border:1px solid #1e293b;border-top:none;padding:20px 26px;">
    <div style="font-size:10px;font-weight:700;color:#3b82f6;letter-spacing:1.2px;text-transform:uppercase;margin-bottom:10px;">Market Overview</div>
    <p style="margin:0;color:#cbd5e1;font-size:14px;line-height:1.75;">{market_overview}</p>
  </div>

  <!-- MACRO OUTLOOK + KEY EVENTS -->
  <div style="background:#0f172a;border:1px solid #1e293b;border-top:none;padding:20px 26px;margin-bottom:14px;border-radius:0 0 10px 10px;">
    <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
      <tr>
        <td width="58%" style="vertical-align:top;padding-right:20px;border-right:1px solid #1e293b;">
          <div style="font-size:10px;font-weight:700;color:#a78bfa;letter-spacing:1.2px;text-transform:uppercase;margin-bottom:10px;">Macro Outlook</div>
          <p style="margin:0;color:#94a3b8;font-size:13px;line-height:1.75;">{macro_outlook}</p>
        </td>
        <td width="42%" style="vertical-align:top;padding-left:20px;">
          <div style="font-size:10px;font-weight:700;color:#f59e0b;letter-spacing:1.2px;text-transform:uppercase;margin-bottom:10px;">Key Events This Week</div>
          <ul style="margin:0;padding:0;list-style:none;">{events_items}</ul>
        </td>
      </tr>
    </table>
  </div>

  <!-- SECTOR SNAPSHOT -->
  <div style="background:#0f172a;border:1px solid #1e293b;border-radius:10px;padding:20px 24px;margin-bottom:14px;">
    <div style="font-size:10px;font-weight:700;color:#34d399;letter-spacing:1.2px;text-transform:uppercase;margin-bottom:14px;">Sector Snapshot — Previous Session</div>
    <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
      {sector_rows}
    </table>
  </div>

  <!-- EARNINGS CALENDAR (this week only) -->
  {earnings_cal}

  <!-- DIVIDER -->
  <div style="border-top:1px solid #1e293b;margin:6px 0 22px;"></div>
  <div style="font-size:10px;font-weight:700;color:#64748b;letter-spacing:2px;text-transform:uppercase;margin-bottom:18px;padding-bottom:10px;border-bottom:1px solid #1e293b;">
    Your Portfolio — Account Summaries
  </div>

  <!-- ACCOUNT SECTIONS -->
  {account_sections}

  <!-- FOOTER -->
  <div style="text-align:center;padding:22px 16px;border-top:1px solid #0f172a;margin-top:10px;">
    <p style="margin:0 0 4px;font-size:11px;color:#1e293b;">Portfolio Intelligence Digest &nbsp;&middot;&nbsp; {date_str}</p>
    <p style="margin:0;font-size:10px;color:#1e3a5f;">For informational purposes only. Not financial advice.</p>
  </div>

</div>
</body>
</html>"""
