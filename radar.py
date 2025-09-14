import json, time, hashlib, requests, feedparser, os, re, datetime as dt

# ---------- TUNABLES ----------
MAX_POSTS = 30                          # 25–35 per your target
DAILY_BUCKET = dt.date.today().isoformat()  # reset dedupe daily
SLACK_WEBHOOK = os.environ["SLACK_WEBHOOK_URL"]

# ---------- SIGNAL VOCAB ----------
# Strong include phrases (at least one should match unless ALWAYS_ALLOW hits)
INCLUDE_PHRASES = [
    # music/event announces
    "announces tour","announced tour","announce tour","world tour","stadium tour",
    "tour dates","adds dates","new dates","residency","headline show","headlining show",
    "on sale","tickets on sale","pre-sale","presale","adds second date","schedules dates",
    # sports fixtures
    "fixture list","fixtures announced","schedule released","draw announced",
    "host city announced","venue selected","host selected",
    # venue/date changes
    "venue change","changed venue","moved to","relocated","rescheduled","date change",
]
# If any of these appear, we allow even without INCLUDE_PHRASES (mega events)
ALWAYS_ALLOW = [
    "olympics","fifa world cup","uefa euro","copa américa","copa america",
    "icc cricket world cup","formula 1","ryder cup","indian wells","super bowl",
]

# Reduce noise (skip if these appear)
EXCLUDE_PHRASES = [
    "review","opinion","editorial","photo gallery","photos:",
    "recap","ratings","viewing figures","rumor","rumour","speculation",
    "lawsuit","merch","box office","chart","streaming numbers","interview"
]

# Artist boost list (still catch others via INCLUDE_PHRASES/ALWAYS_ALLOW)
ARTISTS = [
    # Pop megastars
    "Beyoncé","Taylor Swift","Adele","Ed Sheeran","Harry Styles","Billie Eilish",
    "Dua Lipa","Ariana Grande","Justin Bieber","Olivia Rodrigo","Lady Gaga","Katy Perry","Shakira",
    # Rock / Alt / Legacy
    "Coldplay","Imagine Dragons","Maroon 5","The Killers","Muse","Foo Fighters",
    "Red Hot Chili Peppers","Metallica","Green Day","U2","Oasis","Blur","Arctic Monkeys",
    "Radiohead","The Rolling Stones","ABBA","Genesis","The Eagles","Fleetwood Mac",
    "Bruce Springsteen","Paul McCartney","Elton John","Billy Joel","Madonna","Celine Dion",
    "Guns N' Roses","Kiss","AC/DC","Pearl Jam","Nirvana","The Who","Bon Jovi","Aerosmith",
    "Def Leppard","Journey",
    # Latin / Global
    "Bad Bunny","Karol G","J Balvin","Maluma","Rosalía","Peso Pluma",
    "Rauw Alejandro","Daddy Yankee","Enrique Iglesias","Luis Miguel",
    # Hip-hop / R&B
    "Drake","The Weeknd","Travis Scott","Kendrick Lamar","Kanye West","Nicki Minaj",
    "Doja Cat","Post Malone","Frank Ocean","SZA",
    # K-pop
    "BTS","BLACKPINK","SEVENTEEN","Stray Kids","TWICE","NCT","ENHYPEN","TXT",
    "NewJeans","Aespa","ITZY","IVE","LE SSERAFIM","EXO",
    # Country
    "Garth Brooks","Luke Combs","Morgan Wallen","Chris Stapleton","Carrie Underwood",
    "George Strait","Kacey Musgraves","Dolly Parton",
]

# Country + signal detection (unchanged from earlier, trimmed)
COUNTRIES = [
    "United States","USA","US","UK","United Kingdom","England","Scotland","Wales",
    "Ireland","France","Germany","Spain","Portugal","Italy","Netherlands","Belgium",
    "Sweden","Norway","Denmark","Finland","Poland","Czech Republic","Austria",
    "Switzerland","Greece","Turkey","Russia","Ukraine",
    "Canada","Mexico","Brazil","Argentina","Chile","Colombia","Peru",
    "Japan","South Korea","Korea","China","Hong Kong","Taiwan","Singapore","Malaysia",
    "Thailand","Vietnam","Philippines","India","Pakistan","Bangladesh","Sri Lanka",
    "Australia","New Zealand","South Africa","Nigeria","Kenya","Egypt","Morocco","UAE","Saudi Arabia","Qatar"
]
COUNTRIES_LOWER = [c.lower() for c in COUNTRIES]

SIG_PATTERNS = [
    r"\bfirst (?:time|ever) in (?P<place>[A-Za-z\s]+)",
    r"\bfirst[-\s]?ever\b",
    r"\bafter (?P<years>\d+)\s+years\b",
    r"\bsince (?:19|20)\d{2}\b",
    r"\breunion|reunite|original lineup\b",
    r"\bresidency\b",
    r"\b(stadium|arena) tour\b",
    r"\badds? \d+ (?:new )?dates?\b",
    r"\bannounces? (?:world )?tour\b",
    r"\bvenue change\b",
    r"\bchanged venue\b",
    r"\bmoved to\b",
    r"\brelocated\b",
    r"\brescheduled\b",
    r"\bdate change\b",
]
SIG_REGEX = re.compile("|".join(SIG_PATTERNS), re.IGNORECASE)

# ---------- FEEDS ----------
FEEDS = [
    # Entertainment trades / music news
    "https://www.billboard.com/feed/","https://www.pollstar.com/feed","https://variety.com/feed/",
    "https://www.rollingstone.com/feed/","https://consequence.net/feed/","https://www.nme.com/feed",
    "https://www.spin.com/feed/","https://www.vulture.com/rss/music.xml",
    # Ticketing / operators
    "https://blog.ticketmaster.com/feed/","https://www.livenationentertainment.com/feed/",
    # Festivals
    "https://www.coachella.com/feed/","https://www.glastonburyfestivals.co.uk/feed/","https://www.lollapalooza.com/feed/",
    # Sports wires + press
    "https://feeds.bbci.co.uk/sport/rss.xml","https://www.espn.com/espn/rss/news","https://espnpressroom.com/us/feed/",
    "https://www.reuters.com/rssFeed/sportsNews",
    # Federations / mega events
    "https://www.fifa.com/rss-feeds/index.xml","https://www.uefa.com/rssfeed/uefaeuro.rss","https://www.olympics.com/en/news/rss",
    "https://www.icc-cricket.com/rss/news","https://www.formula1.com/content/fom-website/en/latest/all.xml",
    # Leagues / venues (sample)
    "https://www.premierleague.com/news.rss","https://www.wembleystadium.com/rss","https://www.theo2.co.uk/rss","https://www.sofistadium.com/feed/",
]
FEEDS += [
    # Site-scoped/keyword Google News RSS
    "https://news.google.com/rss/search?q=site:axs.com%20(tour%20OR%20concert%20OR%20dates%20OR%20announce)&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=site:rte.ie%20(entertainment%20OR%20music%20OR%20concert)&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=(tour%20OR%20concert%20OR%20residency%20OR%20reunion)%20announce%20when:14d&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=(%22first%20time%20in%22%20OR%20%22first-ever%22%20OR%20%22after%20*%20years%22)%20(tour%20OR%20concert%20OR%20show%20OR%20residency)%20when:30d&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=(LaLiga%20OR%20%22La%20Liga%22%20OR%20Serie%20A%20OR%20Bundesliga%20OR%20Ligue%201%20OR%20MLS%20OR%20CONMEBOL%20OR%20Copa%20Libertadores%20OR%20Copa%20Sudamericana%20OR%20AFC%20Champions%20League%20OR%20CAF%20Champions%20League)%20when:14d&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=(%22venue%20change%22%20OR%20relocated%20OR%20%22moved%20to%22%20OR%20%22changed%20venue%22)%20(site:mls.com%20OR%20site:premierleague.com%20OR%20site:laliga.com%20OR%20site:bundesliga.com%20OR%20site:ligue1.com%20OR%20site:uefa.com%20OR%20site:fifa.com%20OR%20tour%20OR%20concert)&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=(Argentina%20national%20team%20OR%20AFA%20OR%20Selecci%C3%B3n%20Argentina)%20(venue%20OR%20stadium%20OR%20moved%20OR%20relocated%20OR%20changed)&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=(Valencia%20CF%20OR%20Valencia%20club)%20(venue%20OR%20stadium%20OR%20moved%20OR%20relocated%20OR%20changed)&hl=en-US&gl=US&ceid=US:en",
]

# ---------- DEDUPE (persist across runs) ----------
SEEN_PATH = "seen.json"
seen = {}
if os.path.exists(SEEN_PATH):
    try:
        seen = json.load(open(SEEN_PATH))
    except Exception:
        seen = {}
if DAILY_BUCKET not in seen:
    seen[DAILY_BUCKET] = {"titles": set(), "artists": set()}
# json can't save sets; we'll convert later
def _as_set(x): return set(x) if isinstance(x, list) else (x if isinstance(x, set) else set())

seen[DAILY_BUCKET]["titles"] = _as_set(seen[DAILY_BUCKET].get("titles", []))
seen[DAILY_BUCKET]["artists"] = _as_set(seen[DAILY_BUCKET].get("artists", []))

# ---------- HELPERS ----------
def canonical_key(title: str) -> str:
    core = re.split(r"[-–—:|•·]", title)[0].strip().lower()
    core = re.sub(r"\s+", " ", core)
    return hashlib.sha256(core.encode()).hexdigest()[:16]

def any_in(text: str, words) -> bool:
    t = text.lower()
    return any(w in t for w in words)

def detect_country(text: str) -> str:
    t = text.lower()
    for c, cl in zip(COUNTRIES, COUNTRIES_LOWER):
        if cl in t: return c
    m = re.search(r"\bin\s+([A-Z][A-Za-z\s]+)\b", text)
    return m.group(1).strip() if m else ""

def detect_signal(text: str) -> str:
    m = SIG_REGEX.search(text)
    if not m: return ""
    s = m.group(0).replace("firstever", "first-ever")
    return s.strip().capitalize()

def detect_artist(text: str) -> str:
    # simple pass: match from ARTISTS list
    for a in ARTISTS:
        if a.lower() in text.lower():
            return a
    return ""  # unknown/other (sports, festivals, etc.)

def is_relevant(text: str) -> bool:
    t = text.lower()
    if any_in(t, EXCLUDE_PHRASES):        # throw out reviews/interviews/etc.
        return False
    if any_in(t, ALWAYS_ALLOW):           # mega events pass
        return True
    return any_in(t, INCLUDE_PHRASES)     # otherwise must match include

def score_item(title: str, summary: str) -> int:
    """Higher = more important."""
    t = (title + " " + summary).lower()
    s = 0
    # strong signals
    for k in ["announces tour","tour dates","world tour","stadium tour",
              "residency","adds dates","tickets on sale","fixture","schedule","draw announced",
              "venue change","relocated","moved to","rescheduled"]:
        if k in t: s += 4
    # artists boost
    for a in ARTISTS:
        if a.lower() in t: s += 3; break
    # mega events boost
    for m in ALWAYS_ALLOW:
        if m in t: s += 5
    # country mention mild boost
    for c in COUNTRIES_LOWER:
        if c in t: s += 1; break
    return s

def post_to_slack(title, link, source, country="", signal=""):
    payload = {"title": title, "url": link, "source": source, "country": country or "", "signal": signal or ""}
    r = requests.post(SLACK_WEBHOOK, json=payload, timeout=15)
    print("Slack status:", r.status_code, r.text[:160])

# ---------- COLLECT, FILTER, SCORE ----------
candidates = []
for url in FEEDS:
    try:
        feed = feedparser.parse(url)
    except Exception:
        continue
    for e in feed.entries[:40]:
        title   = getattr(e, "title", "") or ""
        link    = getattr(e, "link", "") or ""
        summary = getattr(e, "summary", "") or ""
        source  = getattr(e, "source", {}).get("title", "") or url
        blob    = f"{title} {summary}"

        if not title or not link:
            continue
        if not is_relevant(blob):
            continue

        score = score_item(title, summary)
        cand = {
            "title": title, "url": link, "source": source,
            "blob": blob, "score": score,
            "artist": detect_artist(blob),
            "country": detect_country(blob),
            "signal": detect_signal(blob),
            "title_key": canonical_key(title)
        }
        candidates.append(cand)

# ---------- DEDUPE (per day): title + artist ----------
titles_seen = seen[DAILY_BUCKET]["titles"]
artists_seen = seen[DAILY_BUCKET]["artists"]

# sort by score desc, then title alpha to stabilize
candidates.sort(key=lambda x: (-x["score"], x["title"]))

final = []
for c in candidates:
    if c["title_key"] in titles_seen:
        continue
    if c["artist"] and (c["artist"] in artists_seen):
        # skip duplicate artist within the day
        continue
    final.append(c)
    titles_seen.add(c["title_key"])
    if c["artist"]:
        artists_seen.add(c["artist"])
    if len(final) >= MAX_POSTS:
        break

# ---------- POST ----------
posted = 0
for c in final:
    try:
        post_to_slack(c["title"], c["url"], c["source"], country=c["country"], signal=c["signal"])
        posted += 1
        time.sleep(1)
    except Exception as err:
        print("Post error:", err)

# ---------- SAVE DEDUPE ----------
seen[DAILY_BUCKET]["titles"] = list(titles_seen)
seen[DAILY_BUCKET]["artists"] = list(artists_seen)
json.dump(seen, open("seen.json", "w"))
print(f"checked={len(candidates)} posted={posted} (cap={MAX_POSTS})")
