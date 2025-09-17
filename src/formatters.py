"""
Markdown + Slack formatting helpers.
"""

from typing import List, Tuple, Dict


def severity_emoji(score: int) -> str:
    """
    Map numeric score to an emoji.
    """
    if score >= 70:
        return "🟥"  # very high risk
    if score >= 55:
        return "🟧"  # medium risk
    return "🟩"      # low risk


def build_markdown_report(
    high: List[Tuple[Dict, int, str]],
    med: List[Tuple[Dict, int, str]]
) -> str:
    """
    Build a Markdown report with High and Medium risk matches.
    """
    lines = ["# Daily INTL Sports Risk Report\n"]

    if high:
        lines.append("## 🔴 High Risk Matches\n")
        for m, score, why in high:
            lines.append(f"- **{m['home']} vs {m['away']}** "
                         f"({m['competition']}, {m['utcKickoff']}) "
                         f"— {score}/100 — {why}")

    if med:
        lines.append("\n## 🟠 Medium Risk Matches\n")
        for m, score, why in med:
            lines.append(f"- **{m['home']} vs {m['away']}** "
                         f"({m['competition']}, {m['utcKickoff']}) "
                         f"— {score}/100 — {why}")

    if not high and not med:
        lines.append("_No elevated risk matches found._")

    return "\n".join(lines)
