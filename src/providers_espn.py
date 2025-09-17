import re
import os
import json
import requests
import datetime as dt
from typing import List, Tuple, Dict, Any

try:
    from bs4 import BeautifulSoup  # type: ignore
except Exception:
    BeautifulSoup = None  # we’ll still try non-BS fallbacks

UTC = dt.timezone.utc

def _fetch(url: str) -> str:
    # Basic headers to look like a browser
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    }
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    return r.text

def _iso_utc(s: str) -> str:
    # Accepts "2025-09-20T18:30Z" or "2025-09-20T18:30:00Z" or with offset
    s = s.strip()
    if s.endswith("Z"):
        try:
            return dt.datetime.fromisoformat(s.replace("Z","+00:00")).astimezone(UTC).isoformat().replace("+00:00","Z")
        except ValueError:
            pass
    # Try without seconds
    try:
        return dt.datetime.fromisoformat(s).astimezone(UTC).isoformat().replace("+00:00","Z")
    except Exception:
        # Last resort: parse yyyy-mm-dd hh:mm or date only
        m = re.search(r"(\d{4}-\d{2}-\d{2})[ T](\d{2}):(\d{2})", s)
        if m:
            y,mn,d = map(int, m.group(1).split("-"))
            hh,mm  = int(m.group(2)), int(m.group(3))
            return dt.datetime(y,mn,d,hh,mm,tzinfo=UTC).isoformat().replace("+00:00","Z")
        m = re.search(r"(\d{4}-\d{2}-\d{2})", s)
        if m:
            y,mn,d = map(int, m.group(1).split("-"))
            return dt.datetime(y,mn,d,0,0,tzinfo=UTC).isoformat().replace("+00:00","Z")
    return ""

def _split_name_to_teams(name: str) -> Tuple[str,str]:
    """
    Try to split an event name like:
      "Arsenal vs Chelsea" or "Chelsea at Arsenal" or "Team A v Team B"
    """
    t = (name or "").strip()
    for sep in [" vs ", " v ", " at "]:
        if sep in t:
            a, b = t.split(sep, 1)
            return a.strip(), b.strip()
    # Fallback: no split
    return "", ""

def _competition_guess(url: str, title: str) -> str:
    # Try to infer comp from title or URL segments
    t = (title or "").strip()
    if t:
        # e.g., "English Premier League Fixtures - ESPN"
        t = re.sub(r"\s+-\s+ESPN.*$", "", t).strip()
        return t
    # URL hints
    # e.g., /soccer/fixtures/_/league/eng.1 -> Premier League
    if "/league/" in url:
        code = url.split("/league/")[-1].split("/")[0]
        return code.upper()
    if "/f1/" in url:
        return "Formula 1"
    if "/nfl/" in url:
        return "NFL"
    if "/nba/" in url:
        return "NBA"
    if "/tennis/" in url:
        return "Tennis"
    if "/golf/" in url:
        return "Golf"
    return "ESPN Fixture"

def _extract_ldjson_events(html: str) -> List[Dict[str,Any]]:
    out = []
    if BeautifulSoup is None:
        return out
    soup = BeautifulSoup(html, "lxml")
    for tag in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            data = json.loads(tag.string or "")
        except Exception:
            continue
        # Could be a list or single dict
        blocks = data if isinstance(data, list) else [data]
        for b in blocks:
            if isinstance(b, dict) and b.get("@type") in ("SportsEvent","Event"):
                out.append(b)
    return out

def _recursive_find_events(obj: Any) -> List[Dict[str,Any]]:
    """
    Search nested JSON for ESPN's event structures.
    We look for dicts containing keys like 'competitions' with 'date' & 'competitors'.
    """
    found: List[Dict[str,Any]] = []
    if isinstance(obj, dict):
        # ESPN scoreboard style
        if "competitions" in obj and isinstance(obj["competitions"], list):
            for comp in obj["competitions"]:
                if not isinstance(comp, dict):
                    continue
                date = comp.get("date")
                competitors = comp.get("competitors")
                if date and isinstance(competitors, list) and len(competitors) >= 2:
                    home, away = "", ""
                    # ESPN flags homeAway
                    for team in competitors:
                        nm = ((team.get("team") or {}).get("displayName") or
                              (team.get("team") or {}).get("name") or "")
                        ha = (team.get("homeAway") or "").lower()
                        if ha == "home" and nm: home = nm
                        if ha == "away" and nm: away = nm
                    if not home or not away:
                        # fallback: just take the first two team names
                        names = [ (t.get("team") or {}).get("displayName") or (t.get("team") or {}).get("name") or ""
                                  for t in competitors ]
                        if len(names) >= 2:
                            home, away = names[0], names[1]
                    found.append({"date": date, "home": home, "away": away})
        # Recurse
        for v in obj.values():
            found.extend(_recursive_find_events(v))
    elif isinstance(obj, list):
        for it in obj:
            found.extend(_recursive_find_events(it))
    return found

def _extract_next_data_events(html: str) -> List[Dict[str,Any]]:
    """
    For Next.js pages ESPN uses, parse the __NEXT_DATA__ JSON.
    """
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>', html, re.DOTALL)
    if not m:
        return []
    try:
        data = json.loads(m.group(1))
    except Exception:
        return []
    # Recursively look for event blocks
    return _recursive_find_events(data)

def parse_espn_page(url: str, html: str, horizon_days: int) -> List[Dict[str,str]]:
    now = dt.datetime.now(tz=UTC)
    end = now + dt.timedelta(days=horizon_days)
    matches: List[Dict[str,str]] = []

    # 1) Try ld+json
    ld_events = _extract_ldjson_events(html)
    title_match = re.search(r"<title>(.*?)</title>", html, re.DOTALL|re.IGNORECASE)
    page_title = title_match.group(1).strip() if title_match else ""
    comp_guess = _competition_guess(url, page_title)

    if ld_events:
        for e in ld_events:
            name = e.get("name") or ""
            start = e.get("startDate") or e.get("startTime") or ""
            if not name or not start:
                continue
            home, away = _split_name_to_teams(name)
            if not home or not away:
                continue
            iso = _iso_utc(start)
            if not iso:
                continue
            dt_iso = dt.datetime.fromisoformat(iso.replace("Z","+00:00"))
            if not (now <= dt_iso <= end):
                continue
            matches.append({
                "home": home,
                "away": away,
                "competition": comp_guess,
                "utcKickoff": iso,
                "status": "SCHEDULED",
                "venue": ""  # ld+json may include location.name; can add if you want
            })

    # 2) Try __NEXT_DATA__ (scoreboard/fixtures)
    if not matches:
        evs = _extract_next_data_events(html)
        for ev in evs:
            iso = _iso_utc(ev.get("date") or "")
            if not iso:
                continue
            dt_iso = dt.datetime.fromisoformat(iso.replace("Z","+00:00"))
            if not (now <= dt_iso <= end):
                continue
            home = (ev.get("home") or "").strip()
            away = (ev.get("away") or "").strip()
            if not home or not away:
                continue
            matches.append({
                "home": home,
                "away": away,
                "competition": comp_guess,
                "utcKickoff": iso,
                "status": "SCHEDULED",
                "venue": ""
            })

    # 3) If still nothing, return empty; caller can try other URLs
    return matches

def get_fixtures_from_espn(urls: List[str], days_ahead: int = 30) -> Tuple[List[Dict[str,str]], List[str]]:
    """
    Pull upcoming fixtures from ESPN pages.
    Returns (matches, errors).
    """
    all_matches: List[Dict[str,str]] = []
    errors: List[str] = []
    for u in urls:
        u = u.strip()
        if not u or u.startswith("#"):
            continue
        try:
            html = _fetch(u)
            matches = parse_espn_page(u, html, horizon_days=days_ahead)
            all_matches.extend(matches)
        except Exception as ex:
            errors.append(f"{u}: {type(ex).__name__}: {ex}")
    # De-dup same pairing/date combos
    seen = set()
    uniq = []
    for m in all_matches:
        key = (m["home"], m["away"], m["utcKickoff"])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(m)
    # Sort by kickoff
    uniq.sort(key=lambda m: m["utcKickoff"])
    return uniq, errors
