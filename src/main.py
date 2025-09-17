import os
import requests
from datetime import datetime

from risk_model import compute_risk, rivalry_bonus, schedule_congestion, venue_signal, weather_signal
from formatters import build_markdown_report, severity_emoji
from providers_espn import get_fixtures_from_espn  # <- make sure src/providers_espn.py exists

REPORT_DIR = "report"
TOP_N = int(os.getenv("TOP_N", "15"))  # how many items to show in Slack

def post_slack(text: str):
    url = os.getenv("SLACK_WEBHOOK_URL")
    if not url:
        return
    try:
        requests.post(url, json={"text": text}, timeout=15)
    except Exception:
        pass

def _read_lines(path: str) -> list:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [ln.strip() for ln in f if ln.strip() and not ln.strip().startswith("#")]

def main() -> int:
    try:
        # ---- config via envs ----
        days_ahead = int(os.getenv("SCAN_DAYS", "30"))
        display_tz = os.getenv("DISPLAY_TZ", "America/New_York")
        HIGH_CUTOFF   = int(os.getenv("HIGH_CUTOFF", "55"))  # lower to surface more “High”
        MEDIUM_CUTOFF = int(os.getenv("MEDIUM_CUTOFF", "40"))

        # ---- pull fixtures from ESPN URLs ----
        urls = _read_lines("espn_urls.txt")
        matches, _errs = get_fixtures_from_espn(urls, days_ahead=days_ahead)

        # empty window case
        if not matches:
            os.makedirs(REPORT_DIR, exist_ok=True)
            with open(os.path.join(REPORT_DIR, "latest.md"), "w", encoding="utf-8") as f:
                f.write("# Daily INTL Sports Risk Report\n\n_No matches available in the scan window._")
            post_slack("✅ No high-risk matches flagged today. (Full report committed to repo)")
            return 0

        # ---- score matches with your model ----
        rows = []
        for m in matches:
            ctx = dict(
                odds_vol=0,  # add odds later if desired
                rivalry=rivalry_bonus(m["home"], m["away"]),
                congestion=0,
                venue=venue_signal(neutral=False, recently_moved=False),
                weather=weather_signal(0.0),
                travel=0,
                catalog_flags=0,
            )
            score, why = compute_risk(m, ctx)
            rows.append((m, score, why))

        high = [(m, s, w) for (m, s, w) in rows if s >= HIGH_CUTOFF]
        med  = [(m, s, w) for (m, s, w) in rows if MEDIUM_CUTOFF <= s < HIGH_CUTOFF]
        high = sorted(high, key=lambda x: x[1], reverse=True)[:TOP_N]
        med  = sorted(med,  key=lambda x: x[1], reverse=True)[:TOP_N]

        # ---- write report (markdown) ----
        os.makedirs(REPORT_DIR, exist_ok=True)
        md = build_markdown_report(high, med)
        with open(os.path.join(REPORT_DIR, "latest.md"), "w", encoding="utf-8") as f:
            f.write(md)

        # ---- Slack messaging ----
        if high:
            header = "❌ *Alert — These Are Upcoming High Risk Matches*"
            preview = header + "\n" + "\n".join(
                [f"{severity_emoji(s)} {m['home']} vs {m['away']} — {s}/100" for (m, s, _) in high]
            )
            post_slack(preview + "\n(Full report committed to repo)")
        else:
            post_slack("✅ No high-risk matches flagged today. (Full report committed to repo)")

        return 0

    except Exception as e:
        post_slack(f"❗ Error in run: {type(e).__name__}: {e}")
        try:
            os.makedirs(REPORT_DIR, exist_ok=True)
            with open(os.path.join(REPORT_DIR, "latest.md"), "w", encoding="utf-8") as f:
                f.write("# Daily INTL Sports Risk Report\n\n_Run encountered an error; see Slack for details._")
        except Exception:
            pass
        return 0

if __name__ == "__main__":
    raise SystemExit(main())
