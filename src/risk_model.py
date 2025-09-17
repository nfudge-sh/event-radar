"""
Risk scoring model for upcoming fixtures.
You can expand these heuristics as needed.
"""

from typing import Tuple, Dict


def rivalry_bonus(home: str, away: str) -> int:
    """
    Simple hardcoded rivalry list.
    You can expand this list with more derbies.
    """
    name = f"{home.lower()} vs {away.lower()}"
    rivalries = [
        ("barcelona", "real madrid"),    # El Clásico
        ("celtic", "rangers"),
        ("arsenal", "tottenham"),
        ("manchester united", "liverpool"),
        ("boca juniors", "river plate"),
        ("fenerbahce", "galatasaray"),
    ]
    for a, b in rivalries:
        if (a in home.lower() and b in away.lower()) or (b in home.lower() and a in away.lower()):
            return 30
    return 0


def schedule_congestion() -> int:
    """
    Stub for fixture congestion (back-to-back games).
    Could be extended to look at actual fixture density.
    """
    return 0


def venue_signal(neutral: bool = False, recently_moved: bool = False) -> int:
    score = 0
    if neutral:
        score += 5
    if recently_moved:
        score += 10
    return score


def weather_signal(severity: float = 0.0) -> int:
    """
    Map weather severity (0.0 – 1.0) to points.
    """
    return int(severity * 20)


def compute_risk(match: Dict, ctx: Dict) -> Tuple[int, str]:
    """
    Compute a risk score for a given match.
    """
    reasons = []

    score = 0

    # Rivalry weight
    if ctx.get("rivalry", 0):
        score += ctx["rivalry"]
        reasons.append("Rivalry/Derby")

    # Venue issues
    if ctx.get("venue", 0):
        score += ctx["venue"]
        reasons.append("Venue considerations")

    # Weather
    if ctx.get("weather", 0):
        score += ctx["weather"]
        reasons.append("Weather risk")

    # Schedule congestion
    if ctx.get("congestion", 0):
        score += ctx["congestion"]
        reasons.append("Congested schedule")

    # Odds / volatility placeholder
    if ctx.get("odds_vol", 0):
        score += ctx["odds_vol"]
        reasons.append("Betting volatility")

    # Travel issues
    if ctx.get("travel", 0):
        score += ctx["travel"]
        reasons.append("Travel disruption")

    # Catalog / flags
    if ctx.get("catalog_flags", 0):
        score += ctx["catalog_flags"]
        reasons.append("Catalog flags")

    return score, ", ".join(reasons) if reasons else "Low baseline risk"
