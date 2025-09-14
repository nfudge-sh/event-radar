import os, re, json, time, hashlib, requests, feedparser, datetime as dt
from email.utils import parsedate_to_datetime

# =========================
# Tunables
# =========================
MAX_POSTS = 30                 # cap daily posts (set 25–35)
MAX_AGE_HOURS = 72             # only keep items published/updated in last 72h
SLACK_WEBHOOK = os.environ["SLACK_WEBHOOK_URL"]
DAILY_BUCKET = dt.date.today().isoformat()   # resets dedupe each day

# =========================
# Event intent (filters)
# =========================
INCLUDE_PHRASES = [
    # music/event announces
    "announces tour","announced tour","announce tour",
    "world tour","stadium tour","arena tour",
    "tour dates","dates announced","adds dates","new dates","extra date","second show",
    "residency","headline show","headlining show",
    "tickets on sale","ticket pre-sale","presale","pre-sale","on sale",
    # sports fixtures / venues
    "fixture list","fixtures announced","schedule released","schedule announced",
    "draw announced","host city announced","host selected","host city selected",
    "venue change","changed venue","moved to","relocated","rescheduled","date change",
]

# These always pass (mega events), even if INCLUDE_PHRASES aren’t present
ALWAYS_ALLOW = [
    "olympics","fifa world cup","uefa euro","copa américa","copa america",
    "icc cricket world cup","formula 1","ryder cup","indian wells","super bowl",
]

# Throw these out (fluff / non-event)
EXCLUDE_PHRASES = [
    "how to watch","when and where to watch","live streaming","livestream",
    "tv channel","broadcast info","what time is","kick-off time","line-ups",
    "preview","odds","prediction","rumor","rumour","speculation","transfer",
    "injury","sidelined","contract","interview","feature","opinion","column",
    "review","recap","ratings","photo gallery","photos:","fan is visiting","budget",
    "box office","chart","streaming numbers","behind the scenes"
]

# Artist boost list (others still caught via INCLUDE/ALWAYS_ALLOW)
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

# Countries (for country detection boost)
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

# =========================
# Sources (RSS + Google News RSS)
# =========================
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
    "https://www.premierleague.com/news.rss","https://www.wembleystadium.com/rss",
    "https://www.theo2.co.uk/rss","https://www.sofistadium.com/feed/",
]
FEEDS += [
    # Site-scoped/keyword Google News RSS
    "https://news.google.com/rss/search?q=site:axs.com%20(tour%20OR%20concert%20OR%20dates%20OR%20announce)&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=site:rte.ie%20(entertainment%20OR%20music%20OR%20concert)&hl=en-US&gl=US&ceid=US:en",
    # Global tours / first-time / reunion
    "https://news.google.com/rss/search?q=(tour%20OR%20concert%20OR%20residency%20OR%20reunion)%20announce%20when:14d&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=(%22first%20time%20in%22%20OR%20%22first-ever%22%20OR%20%22after%20*%20years%22)%20(tour%20OR%20concert%20OR%20show%20OR%20residency)%20when:30d&hl=en-US&gl=US&ceid=US:en",
    # Soccer: broad leagues sweep
    "https://news.google.com/rss/search?q=(LaLiga%20OR%20%22La%20Liga%22%20OR%20Serie%20A%20OR%20Bundesliga%20OR%20Ligue%201%20OR%20MLS%20OR%20CONMEBOL%20OR%20Copa%20Libertadores%20OR%20Copa%20Sudamericana%20OR%20AFC%20Champions%20League%20OR%20CAF%20Champions%20League)%20when:14d&hl=en-US&gl=US&ceid=US:en",
    # Venue changes / relocations
    "https://news.google.com/rss/search?q=(%22venue%20change%22%20OR%20relocated%20OR%20%22moved%20to%22%20OR%20%22changed%20venue%22)%20(site:mls.com%20OR%20site:premierleague.com%20OR%20site:laliga.com%20OR%20site:bundesliga.com%20OR%20site:ligue1.com%20OR%20site:uefa.com%20OR%20site:fifa.com%20OR%20tour%20OR%20concert)&hl=en-US&gl=US&ceid=US:en",
    # Team/club-specific examples
    "https://news.google.com/rss/search?q=(Argentina%20national%20team%20OR%20AFA%20OR%20Selecci%C3%B3n%20Argentina)%20(venue%20OR%20stadium%20OR%20moved%20OR%20relocated%20OR%20changed)&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=(Valencia%20CF%20OR%20Valencia%20club)%20(venue%20OR%20stadium%20OR%20moved%20OR%20relocated%20OR%20changed)&hl=en-US&gl=US&ceid=US:en",
]

# =========================
# Dedupe (persist per day)
# =========================
SEEN_PATH = "seen.json"
seen = {}
if os.path.exists(SEEN_PATH):
    try:
        seen = json.load(open(SEEN_PATH))
    except Exception:
        seen = {}
if DAILY_BUCKET not in seen:
    seen[DAILY_BUCKET] = {"titles": [], "artists": []}  # store as lists for JSON safety
titles_seen = set(seen[DAILY_BUCKET].get("titles", []))
artists_seen = set(seen[DAILY_BUCKET].get("artists", []))

# =========================
# Helpers
# =========================
def canonical_key(title: str) -> str:
    core = re.split(r"[-–—:|•·]", title)[0].strip().lower()
    core = re.sub(r"\s+", " ", core)
    return hashlib.sha256(core.encode()).hexdigest()[:16]

def any_in(text: str, words) -> bool:
    t = text.lower()
    return any(w in t for w in words)

def entry_datetime(e):
    # try common RFC822 fields
    for fld in ("published", "updated", "pubDate"):
        val = getattr(e, fld, "") or (e.get(fld, "") if isinstance(e, dict) else "")
        if val:
            try:
                return parsedate_to_datetime(val)
            except Exception:
                pass
    # feedparser structs
    for fld in ("published_parsed","updated_parsed"):
        val = getattr(e, fld, None)
        if val:
            try:
                return dt.datetime(*val[:6], tzinfo=dt.timezone.utc)
            except Exception:
                pass
    return None

def is_recent(e, max_hours=MAX_AGE_HOURS):
    d = entry_datetime(e)
    if not d:
        return False
    if not d.tzinfo:
        d = d.replace(tzinfo=dt.timezone.utc)
    now = dt.datetime.now(dt.timezone.utc)
    return (now - d).total_seconds() <= max_hours * 3600

def is_relevant(text: str) -> bool:
    t = text.lower()
    if any_in(t, EXCLUDE_PHRASES):
        return False
    if any_in(t, ALWAYS_ALLOW):
        return True
    return any_in(t, INCLUDE_PHRASES)

def detect_country(text: str) -> str:
    t = text.lower()
    for c, cl in zip(COUNTRIES, COUNTRIES_LOWER):
        if cl in t: return c
    m = re.search(r"\bin\s+([A-Z][A-Za-z\s]+)\b", text)  # e.g., "in Vietnam"
    return m.group(1).strip() if m else ""

def detect_signal(text: str) -> str:
    m = SIG_REGEX.search(text)
    if not m: return ""
    s = m.group(0).replace("firstever", "first-ever")
    return s.strip().capitalize()

def detect_artist(text: str) -> str:
    low = text.lower()
    for a in ARTISTS:
        if a.lower() in low:
            return a
    return ""

def score_item(title: str, summary: str) -> int:
    t = (title + " " + summary).lower()
    s = 0
    # strong signals
    for k in ["announces tour","tour dates","world tour","stadium tour","residency",
              "adds dates","tickets on sale","fixture","schedule released","draw announced",
              "venue change","relocated","moved to","rescheduled"]:
        if k in t: s += 4
    # artist boost
    for a in ARTISTS:
        if a.lower() in t: s += 3; break
    # mega event boost
    for m in ALWAYS_ALLOW:
        if m in t: s += 5
    # country mention mild boost
    for c in COUNTRIES_LOWER:
        if c in t: s += 1; break
    return s

def post_to_slack(title, link, source, country="", signal=""):
    payload = {
        # variables for Slack Workflow
        "title": title or "",
        "url": link or "",
        "source": source or "",
        "country": country or "",
        "signal": signal or "",
        # fallback for classic Incoming Webhook
        "text": f"🎟️ {title}\n• Source: {source} • Country: {country}\n• {signal}\n🔗 {link}"
    }
    r = requests.post(SLACK_WEBHOOK, json=payload, timeout=15)
    print("Slack status:", r.status_code, r.text[:160])

# =========================
# Collect → Filter → Score
# =========================
candidates = []
for url in FEEDS:
    try:
        feed = feedparser.parse(url)
    except Exception:
        continue
    for e in feed.entries[:40]:
        if not is_recent(e):    # freshness gate
            continue

        title   = getattr(e, "title", "") or ""
        link    = getattr(e, "link", "") or ""
        summary = getattr(e, "summary", "") or ""
        source  = getattr(e, "source", {}).get("title", "") or url
        blob    = f"{title} {summary}"

        if not title or not link:
            continue
        if not is_relevant(blob):
            continue

        candidates.append({
            "title": title,
            "url": link,
            "source": source,
            "blob": blob,
            "score": score_item(title, summary),
            "artist": detect_artist(blob),
            "country": detect_country(blob),
            "signal": detect_signal(blob),
            "title_key": canonical_key(title),
        })

# =========================
# Daily de-dupe & cap
# =========================
candidates.sort(key=lambda x: (-x["score"], x["title"]))  # rank
final = []
for c in candidates:
    if c["title_key"] in titles_seen:
        continue
    if c["artist"] and (c["artist"] in artists_seen):
        continue  # only one post per artist per day
    final.append(c)
    titles_seen.add(c["title_key"])
    if c["artist"]:
        artists_seen.add(c["artist"])
    if len(final) >= MAX_POSTS:
        break

# =========================
# Post to Slack
# =========================
posted = 0
for c in final:
    try:
        post_to_slack(c["title"], c["url"], c["source"],
                      country=c["country"], signal=c["signal"])
        posted += 1
        time.sleep(1)
    except Exception as err:
        print("Post error:", err)

# =========================
# Persist dedupe (no git push needed)
# =========================
seen[DAILY_BUCKET] = {
    "titles": list(titles_seen),
    "artists": list(artists_seen)
}
with open("seen.json", "w") as f:
    json.dump(seen, f)

print(f"checked={len(candidates)} posted={posted} cap={MAX_POSTS} window={MAX_AGE_HOURS}h")
