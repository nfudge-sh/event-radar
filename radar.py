import json, time, hashlib, requests, feedparser, os, re

# ---------- CONFIG ----------
KEYS = [
    "tour","concert","residency","reunion","stadium","arena",
    "adds dates","announces dates","first time","since 20","since 19",
    "venue change","changed venue","moved to","relocated","rescheduled","date change"
]

ARTISTS = [
    # Pop megastars
    "Beyoncé","Taylor Swift","Adele","Ed Sheeran","Harry Styles",
    "Billie Eilish","Dua Lipa","Ariana Grande","Justin Bieber",
    "Olivia Rodrigo","Lady Gaga","Katy Perry","Shakira",
    # Rock / Alt
    "Coldplay","Imagine Dragons","Maroon 5","The Killers","Muse",
    "Foo Fighters","Red Hot Chili Peppers","Metallica","Green Day",
    "U2","Oasis","Blur","Arctic Monkeys","Radiohead","The Rolling Stones",
    # Latin / Global
    "Bad Bunny","Karol G","J Balvin","Maluma","Rosalía","Peso Pluma",
    "Rauw Alejandro","Daddy Yankee","Enrique Iglesias","Luis Miguel",
    # Hip-hop / R&B
    "Drake","The Weeknd","Travis Scott","Kendrick Lamar","Kanye West",
    "Nicki Minaj","Doja Cat","Post Malone","Frank Ocean","SZA",
    # K-pop
    "BTS","BLACKPINK","SEVENTEEN","Stray Kids","TWICE","NCT","ENHYPEN",
    "TXT","NewJeans","Aespa","ITZY","IVE","LE SSERAFIM","EXO",
    # Legacy / Stadium acts
    "ABBA","Genesis","The Eagles","Fleetwood Mac","Bruce Springsteen",
    "Paul McCartney","Elton John","Billy Joel","Madonna","Celine Dion",
    "Guns N' Roses","Kiss","AC/DC","Pearl Jam","Nirvana","The Who",
    "Bon Jovi","Aerosmith","Def Leppard","Journey",
    # Country
    "Garth Brooks","Luke Combs","Morgan Wallen","Chris Stapleton",
    "Carrie Underwood","George Strait","Kacey Musgraves","Dolly Parton"
]

SLACK_WEBHOOK = os.environ["SLACK_WEBHOOK_URL"]  # set in GitHub Secrets

FEEDS = [
    # Entertainment trades / music news
    "https://www.billboard.com/feed/",
    "https://www.pollstar.com/feed",
    "https://variety.com/feed/",
    "https://www.rollingstone.com/feed/",
    "https://consequence.net/feed/",
    "https://www.nme.com/feed",
    "https://www.spin.com/feed/",
    "https://www.vulture.com/rss/music.xml",
    # Ticketing / operators
    "https://blog.ticketmaster.com/feed/",
    "https://www.livenationentertainment.com/feed/",
    # Festivals (sample)
    "https://www.coachella.com/feed/",
    "https://www.glastonburyfestivals.co.uk/feed/",
    "https://www.lollapalooza.com/feed/",
    # Global sports (wires + press)
    "https://feeds.bbci.co.uk/sport/rss.xml",
    "https://www.espn.com/espn/rss/news",
    "https://espnpressroom.com/us/feed/",
    "https://www.reuters.com/rssFeed/sportsNews",
    # Federations / mega events
    "https://www.fifa.com/rss-feeds/index.xml",
    "https://www.uefa.com/rssfeed/uefaeuro.rss",
    "https://www.olympics.com/en/news/rss",
    "https://www.icc-cricket.com/rss/news",
    "https://www.formula1.com/content/fom-website/en/latest/all.xml",
    # Soccer (league/org news)
    "https://www.premierleague.com/news.rss",
    # Stadiums/arenas (sample)
    "https://www.wembleystadium.com/rss",
    "https://www.theo2.co.uk/rss",
    "https://www.sofistadium.com/feed/",
]
FEEDS += [
    # Site-scoped sweeps (AXS + RTÉ)
    "https://news.google.com/rss/search?q=site:axs.com%20(tour%20OR%20concert%20OR%20dates%20OR%20announce)&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=site:rte.ie%20(entertainment%20OR%20music%20OR%20concert)&hl=en-US&gl=US&ceid=US:en",
    # Global tours / first-time / reunion
    "https://news.google.com/rss/search?q=(tour%20OR%20concert%20OR%20residency%20OR%20reunion)%20announce%20when:14d&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=(%22first%20time%20in%22%20OR%20%22first-ever%22%20OR%20%22after%20*%20years%22)%20(tour%20OR%20concert%20OR%20show%20OR%20residency)%20when:30d&hl=en-US&gl=US&ceid=US:en",
    # Soccer: broad leagues sweep
    "https://news.google.com/rss/search?q=(LaLiga%20OR%20%22La%20Liga%22%20OR%20Serie%20A%20OR%20Bundesliga%20OR%20Ligue%201%20OR%20MLS%20OR%20CONMEBOL%20OR%20Copa%20Libertadores%20OR%20Copa%20Sudamericana%20OR%20AFC%20Champions%20League%20OR%20CAF%20Champions%20League)%20when:14d&hl=en-US&gl=US&ceid=US:en",
    # Venue changes / relocations (soccer + concerts)
    "https://news.google.com/rss/search?q=(%22venue%20change%22%20OR%20relocated%20OR%20%22moved%20to%22%20OR%20%22changed%20venue%22)%20(site:mls.com%20OR%20site:premierleague.com%20OR%20site:laliga.com%20OR%20site:bundesliga.com%20OR%20site:ligue1.com%20OR%20site:uefa.com%20OR%20site:fifa.com%20OR%20tour%20OR%20concert)&hl=en-US&gl=US&ceid=US:en",
    # Team/club-specific signals (Argentina & Valencia example)
    "https://news.google.com/rss/search?q=(Argentina%20national%20team%20OR%20AFA%20OR%20Selecci%C3%B3n%20Argentina)%20(venue%20OR%20stadium%20OR%20moved%20OR%20relocated%20OR%20changed)&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=(Valencia%20CF%20OR%20Valencia%20club)%20(venue%20OR%20stadium%20OR%20moved%20OR%20relocated%20OR%20changed)&hl=en-US&gl=US&ceid=US:en",
]

# ---------- COUNTRY & SIGNAL DETECTION ----------
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

# ---------- DEDUPE ----------
SEEN_PATH = "seen.json"
seen = set()
if os.path.exists(SEEN_PATH):
    try:
        seen = set(json.load(open(SEEN_PATH)))
    except Exception:
        seen = set()

def canonical_key(title: str) -> str:
    core = re.split(r"[-–—:|•·]", title)[0].strip().lower()
    core = re.sub(r"\s+", " ", core)
    return hashlib.sha256(core.encode()).hexdigest()[:16]

# ---------- HELPERS ----------
def is_hit(text: str) -> bool:
    t = text.lower()
    if any(a.lower() in t for a in ARTISTS): return True
    if any(k in t for k in KEYS): return True
    return False

def detect_country(text: str) -> str:
    t = text.lower()
    for c, cl in zip(COUNTRIES, COUNTRIES_LOWER):
        if cl in t: return c
    m = re.search(r"\bin\s+([A-Z][A-Za-z\s]+)\b", text)  # e.g., "in Vietnam"
    if m: return m.group(1).strip()
    return ""

def detect_signal(text: str) -> str:
    m = SIG_REGEX.search(text)
    if not m: return ""
    s = m.group(0).replace("firstever", "first-ever")
    return s.strip().capitalize()

def post_to_slack(title, link, source, country="", signal=""):
    payload = {
        "title": title,
        "url": link,
        "source": source,
        "country": country or "",
        "signal": signal or ""
    }
    r = requests.post(SLACK_WEBHOOK, json=payload, timeout=15)
    print("Slack status:", r.status_code, r.text[:200])

# ---------- MAIN ----------
posted = 0
for url in FEEDS:
    feed = feedparser.parse(url)
    for e in feed.entries[:40]:
        title = getattr(e, "title", "")
        link = getattr(e, "link", "")
        summary = getattr(e, "summary", "")
        source = getattr(e, "source", {}).get("title", "") or url

        if not title or not link:
            continue
        blob = f"{title} {summary}"
        if not is_hit(blob):
            continue

        key = canonical_key(title)
        if key in seen:
            continue

        try:
            country = detect_country(blob)
            signal = detect_signal(blob)
            post_to_slack(title, link, source, country=country, signal=signal)
            seen.add(key)
            posted += 1
            time.sleep(1)  # avoid bursts
        except Exception as err:
            print("Post error:", err)
            continue

# keep last 5000 dedupe keys
json.dump(list(seen)[-5000:], open(SEEN_PATH, "w"))
print(f"posted={posted}")
