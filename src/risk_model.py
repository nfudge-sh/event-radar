"""
Risk scoring model — rivalry-first.
- Uses rivalry/alias DB so rivalries ALWAYS surface.
- Other signals remain additive and tunable.
"""

from typing import Tuple, Dict
from rivalries import detect_rivalry


def rivalry_bonus(home: str, away: str, sport_hint: str = "") -> Tuple[int, str, bool]:
    """
    Returns (points, label, is_rivalry).
    Points are high enough to guarantee the match clears any HIGH threshold.
    """
    is_riv, pts, label = detect_rivalry(home, away, sport_hint or None)
    if is_riv:
        return pts, label or "Rivalry/Derby", True
    return 0, "", False


def schedule_congestion() -> int:
    return 0


def venue_signal(neutral: bool = False, recently_moved: bool = False) -> int:
    score = 0
    if neutral:
        score += 5
    if recently_moved:
        score += 10
    return score


def weather_signal(severity: float = 0.0) -> int:
    return int(severity * 20)


def compute_risk(match: Dict, ctx: Dict) -> Tuple[int, str]:
    """
    Compute a risk score for a given match dict:
    expects match["home"], match["away"]; optional ctx["sport_hint"].
    """
    reasons = []
    score = 0

    # 1) Rivalry: dominant
    rv_pts, rv_label, is_rival = rivalry_bonus(
        match.get("home", ""), match.get("away", ""), ctx.get("sport_hint", "")
    )
    if rv_pts > 0:
        score += rv_pts
        reasons.append(rv_label or "Rivalry")

    # 2) Other additive signals
    for key, label in [
        ("venue", "Venue considerations"),
        ("weather", "Weather risk"),
        ("congestion", "Congested schedule"),
        ("odds_vol", "Betting volatility"),
        ("travel", "Travel disruption"),
        ("catalog_flags", "Catalog flags"),
    ]:
        val = ctx.get(key, 0)
        if val:
            score += val
            reasons.append(label)

    # Bound score to 100
    score = min(score, 100)

    # If rivalry, guarantee surfacing downstream by tagging in reasons
    if is_rival and "Rivalry" not in " ".join(reasons):
        reasons.append("Rivalry")

    return score, ", ".join(reasons) if reasons else "Low baseline risk"
