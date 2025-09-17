# -*- coding: utf-8 -*-
"""
Global rivalry & alias database (teams + players), used to detect rivalries
robustly from scraped names. Add/extend freely.

Conventions
-----------
- Canonical names are lowercase (e.g., "manchester united").
- Aliases include short names, nicknames, other languages, common media variants.
- RIVALRIES covers clubs, national teams, players, and individual-sport rivalries.

Detection
---------
- We map any seen name to a canonical token via REVERSE_ALIASES (substring match).
- Then we check if the (canon_a, canon_b) pair is in RIVALRY_INDEX (order agnostic).
"""

from typing import Dict, List, Tuple, Optional

# --- Aliases (teams & players) ---

ALIASES: Dict[str, List[str]] = {
    # Football / Soccer (clubs)
    "real madrid": ["real madrid", "real", "r. madrid", "realmadrid", "real madrid cf"],
    "barcelona": ["barcelona", "fc barcelona", "barça", "barca"],
    "manchester united": ["manchester united", "man utd", "man united", "man u", "manchester utd"],
    "liverpool": ["liverpool", "liverpool fc", "liverpool football club", "lfc"],
    "arsenal": ["arsenal", "arsenal fc", "gunners"],
    "tottenham hotspur": ["tottenham hotspur", "tottenham", "spurs"],
    "inter milan": ["inter milan", "internazionale", "fc internazionale", "inter"],
    "ac milan": ["ac milan", "milan", "a.c. milan"],
    "borussia dortmund": ["borussia dortmund", "dortmund", "bvb"],
    "bayern munich": ["bayern munich", "bayern", "fc bayern", "fc bayern münchen", "bayern muenchen"],
    "schalke 04": ["schalke 04", "schalke", "fc schalke 04"],
    "ajax": ["ajax", "afc ajax", "ajax amsterdam"],
    "feyenoord": ["feyenoord", "rotterdam"],
    "roma": ["roma", "as roma", "a.s. roma"],
    "lazio": ["lazio", "ss lazio", "s.s. lazio"],
    "juventus": ["juventus", "juve"],
    "olympiacos": ["olympiacos", "olympiakos", "olympiacos fc"],
    "panathinaikos": ["panathinaikos", "panathinaikos fc"],
    "fenerbahce": ["fenerbahce", "fenerbahçe", "fener"],
    "galatasaray": ["galatasaray", "galatasaray sk", "gala"],
    "al ahly": ["al ahly", "ahly"],
    "zamalek": ["zamalek", "zamalek sc"],
    "flamengo": ["flamengo", "cr flamengo"],
    "fluminense": ["fluminense", "fluminense fc"],
    "boca juniors": ["boca juniors", "boca", "ca boca juniors"],
    "river plate": ["river plate", "river", "ca river plate"],
    "club américa": ["club américa", "club america", "américa", "america (mex)"],
    "chivas": ["chivas", "cd guadalajara", "guadalajara"],

    # Football / Soccer (national teams)
    "brazil": ["brazil", "brasil"],
    "argentina": ["argentina"],
    "england": ["england"],
    "germany": ["germany", "deutschland"],
    "italy": ["italy", "italia"],
    "france": ["france"],
    "mexico": ["mexico", "méxico"],
    "united states": ["united states", "usa", "u.s.a.", "usmnt"],
    "japan": ["japan", "nippon"],
    "south korea": ["south korea", "korea republic"],

    # NBA teams (canonical city + nickname)
    "los angeles lakers": ["los angeles lakers", "lakers"],
    "boston celtics": ["boston celtics", "celtics", "bos"],
    "chicago bulls": ["chicago bulls", "bulls"],
    "detroit pistons": ["detroit pistons", "pistons"],
    "new york knicks": ["new york knicks", "knicks"],
    "miami heat": ["miami heat", "heat"],
    "indiana pacers": ["indiana pacers", "pacers"],
    "golden state warriors": ["golden state warriors", "warriors", "gsw"],
    "cleveland cavaliers": ["cleveland cavaliers", "cavaliers", "cavs"],
    "philadelphia 76ers": ["philadelphia 76ers", "sixers", "76ers"],

    # NFL teams (common short forms too)
    "green bay packers": ["green bay packers", "packers", "gb"],
    "chicago bears": ["chicago bears", "bears", "chi"],
    "dallas cowboys": ["dallas cowboys", "cowboys", "dal"],
    "washington commanders": ["washington commanders", "commanders", "washington"],
    "pittsburgh steelers": ["pittsburgh steelers", "steelers", "pit"],
    "baltimore ravens": ["baltimore ravens", "ravens", "bal"],
    "new york giants": ["new york giants", "giants", "nyg"],
    "philadelphia eagles": ["philadelphia eagles", "eagles", "phi"],
    "san francisco 49ers": ["san francisco 49ers", "49ers", "sf"],
    "las vegas raiders": ["las vegas raiders", "oakland raiders", "raiders", "lv"],

    # MLB teams
    "new york yankees": ["new york yankees", "yankees", "nyy"],
    "boston red sox": ["boston red sox", "red sox", "bos"],
    "los angeles dodgers": ["los angeles dodgers", "dodgers", "lad"],
    "san francisco giants": ["san francisco giants", "giants", "sfg"],
    "chicago cubs": ["chicago cubs", "cubs", "chc"],
    "st. louis cardinals": ["st. louis cardinals", "st louis cardinals", "cardinals", "stl"],
    "new york mets": ["new york mets", "mets", "nym"],
    "philadelphia phillies": ["philadelphia phillies", "phillies", "phi"],

    # NHL teams
    "montreal canadiens": ["montreal canadiens", "canadiens", "habs", "mtl"],
    "toronto maple leafs": ["toronto maple leafs", "maple leafs", "leafs", "tor"],
    "boston bruins": ["boston bruins", "bruins", "bos"],
    "colorado avalanche": ["colorado avalanche", "avalanche", "avs", "col"],
    "detroit red wings": ["detroit red wings", "red wings", "det"],
    "edmonton oilers": ["edmonton oilers", "oilers", "edm"],
    "calgary flames": ["calgary flames", "flames", "cgy"],
    "new york rangers": ["new york rangers", "rangers", "nyr"],
    "new york islanders": ["new york islanders", "islanders", "isles", "nyi"],
    "pittsburgh penguins": ["pittsburgh penguins", "penguins", "pens", "pit"],
    "philadelphia flyers": ["philadelphia flyers", "flyers", "phi"],

    # Tennis (players)
    "roger federer": ["roger federer", "federer"],
    "rafael nadal": ["rafael nadal", "nadal"],
    "novak djokovic": ["novak djokovic", "djokovic", "nole"],
    "serena williams": ["serena williams", "serena"],
    "venus williams": ["venus williams", "venus"],
    "martina navratilova": ["martina navratilova", "navratilova"],
    "chris evert": ["chris evert", "evert"],
    "pete sampras": ["pete sampras", "sampras"],
    "andre agassi": ["andre agassi", "agassi"],
    "bjorn borg": ["bjorn borg", "björn borg", "borg"],
    "john mcenroe": ["john mcenroe", "mcenroe"],

    # F1 (drivers)
    "ayrton senna": ["ayrton senna", "senna"],
    "alain prost": ["alain prost", "prost"],
    "james hunt": ["james hunt", "hunt"],
    "niki lauda": ["niki lauda", "lauda"],
    "michael schumacher": ["michael schumacher", "schumacher"],
    "mika hakkinen": ["mika hakkinen", "häkkinen", "haekkinen", "hakkinen"],
    "lewis hamilton": ["lewis hamilton", "hamilton"],
    "sebastian vettel": ["sebastian vettel", "vettel"],
    "max verstappen": ["max verstappen", "verstappen"],
    "nico rosberg": ["nico rosberg", "rosberg"],

    # Golf (players / teams)
    "jack nicklaus": ["jack nicklaus", "nicklaus"],
    "arnold palmer": ["arnold palmer", "palmer"],
    "tiger woods": ["tiger woods", "tiger"],
    "phil mickelson": ["phil mickelson", "mickelson", "lefty"],
    "united states (golf)": ["united states", "team usa", "usa (golf)", "us ryder cup"],
    "europe (golf)": ["europe", "team europe", "europe ryder cup"],
}

# Build reverse lookup for quick canonical mapping
REVERSE_ALIASES: List[Tuple[str, str]] = []
for canon, names in ALIASES.items():
    for n in names:
        REVERSE_ALIASES.append((canon, n.lower()))

def to_canonical(name: str) -> Optional[str]:
    """
    Map any input name to a canonical token using substring inclusion over aliases.
    """
    if not name:
        return None
    s = name.strip().lower()
    # fast path: direct alias match
    for canon, alias in REVERSE_ALIASES:
        if s == alias:
            return canon
    # substring containment (handles "Manchester Utd FC", etc.)
    for canon, alias in REVERSE_ALIASES:
        if alias in s:
            return canon
    return None


# --- Rivalries (unordered pairs; teams, nations, players, or team vs team in other sports) ---

RIVALRIES: List[Tuple[str, str, str]] = [
    # Soccer clubs
    ("soccer", "real madrid", "barcelona"),                 # El Clásico
    ("soccer", "manchester united", "liverpool"),           # Northwest Derby
    ("soccer", "arsenal", "tottenham hotspur"),             # North London Derby
    ("soccer", "ac milan", "inter milan"),                  # Derby della Madonnina
    ("soccer", "borussia dortmund", "bayern munich"),       # Der Klassiker
    ("soccer", "borussia dortmund", "schalke 04"),          # Revierderby
    ("soccer", "ajax", "feyenoord"),                        # De Klassieker
    ("soccer", "roma", "lazio"),                            # Derby della Capitale
    ("soccer", "juventus", "inter milan"),                  # Derby d’Italia
    ("soccer", "olympiacos", "panathinaikos"),              # Eternal Enemies
    ("soccer", "fenerbahce", "galatasaray"),                # Intercontinental Derby
    ("soccer", "al ahly", "zamalek"),                       # Cairo Derby
    ("soccer", "flamengo", "fluminense"),                   # Fla–Flu
    ("soccer", "boca juniors", "river plate"),              # Superclásico
    ("soccer", "club américa", "chivas"),                   # Súper Clásico (Mexico)

    # Soccer national teams
    ("soccer", "brazil", "argentina"),
    ("soccer", "england", "scotland"),
    ("soccer", "england", "germany"),
    ("soccer", "argentina", "england"),
    ("soccer", "france", "italy"),
    ("soccer", "mexico", "united states"),
    ("soccer", "japan", "south korea"),
    ("soccer", "brazil", "uruguay"),

    # NBA
    ("nba", "boston celtics", "los angeles lakers"),
    ("nba", "chicago bulls", "detroit pistons"),
    ("nba", "new york knicks", "miami heat"),
    ("nba", "new york knicks", "indiana pacers"),
    ("nba", "golden state warriors", "cleveland cavaliers"),
    ("nba", "boston celtics", "philadelphia 76ers"),

    # NFL
    ("nfl", "green bay packers", "chicago bears"),
    ("nfl", "dallas cowboys", "washington commanders"),
    ("nfl", "pittsburgh steelers", "baltimore ravens"),
    ("nfl", "new york giants", "philadelphia eagles"),
    ("nfl", "san francisco 49ers", "dallas cowboys"),
    ("nfl", "las vegas raiders", "kansas city chiefs"),  # chiefs implicit via alias? add if needed

    # MLB
    ("mlb", "new york yankees", "boston red sox"),
    ("mlb", "los angeles dodgers", "san francisco giants"),
    ("mlb", "chicago cubs", "st. louis cardinals"),
    ("mlb", "new york mets", "philadelphia phillies"),
    ("mlb", "los angeles dodgers", "new york yankees"),  # historic WS rivalry

    # NHL
    ("nhl", "montreal canadiens", "toronto maple leafs"),
    ("nhl", "boston bruins", "montreal canadiens"),
    ("nhl", "detroit red wings", "colorado avalanche"),
    ("nhl", "edmonton oilers", "calgary flames"),
    ("nhl", "new york rangers", "new york islanders"),
    ("nhl", "pittsburgh penguins", "philadelphia flyers"),

    # Tennis (players)
    ("tennis", "roger federer", "rafael nadal"),
    ("tennis", "novak djokovic", "rafael nadal"),
    ("tennis", "roger federer", "novak djokovic"),
    ("tennis", "chris evert", "martina navratilova"),
    ("tennis", "serena williams", "venus williams"),
    ("tennis", "pete sampras", "andre agassi"),
    ("tennis", "bjorn borg", "john mcenroe"),

    # F1 (drivers)
    ("f1", "ayrton senna", "alain prost"),
    ("f1", "james hunt", "niki lauda"),
    ("f1", "michael schumacher", "mika hakkinen"),
    ("f1", "lewis hamilton", "sebastian vettel"),
    ("f1", "max verstappen", "lewis hamilton"),
    ("f1", "lewis hamilton", "nico rosberg"),

    # Golf (players / teams)
    ("golf", "jack nicklaus", "arnold palmer"),
    ("golf", "tiger woods", "phil mickelson"),
    ("golf", "united states (golf)", "europe (golf)"),  # Ryder Cup
]

# quick set for matching without order
RIVALRY_INDEX = {tuple(sorted((a, b))): sport for (sport, a, b) in RIVALRIES}


def detect_rivalry(name_a: str, name_b: str, sport_hint: Optional[str] = None) -> Tuple[bool, int, str]:
    """
    Return (is_rivalry, weight, label)
    - Matches aliases to canonical; checks pair in RIVALRY_INDEX
    - sport_hint: optional ("soccer","nba","nfl","mlb","nhl","tennis","f1","golf")
    - weight: very high so rivalry is always surfaced
    """
    ca = to_canonical(name_a or "")
    cb = to_canonical(name_b or "")
    if not ca or not cb:
        return (False, 0, "")
    key = tuple(sorted((ca, cb)))
    sport = RIVALRY_INDEX.get(key)
    if sport is None:
        return (False, 0, "")
    if sport_hint and sport_hint.lower() != sport.lower():
        # Allow cross-sport if aliases overlap oddly; usually fine to ignore the hint
        pass
    # Make rivalries ALWAYS surface: give a big weight (>= 100)
    label = f"Rivalry: {name_a} vs {name_b}"
    return (True, 100, label)
