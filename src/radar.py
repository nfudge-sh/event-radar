# radar.py
import os, re, json, time, hashlib, requests, feedparser, datetime as dt
from email.utils import parsedate_to_datetime
from providers import get_all_feeds

# =========================
# Tunables
# =========================
MAX_POSTS = 30                 # cap daily posts
MAX_AGE_HOURS = 72             # only keep items published in last 72h
DEDUP_DAYS = 3                 # rolling dedupe window
ENTRIES_PER_FEED = 250         # scan deeper per feed page
SLACK_WEBHOOK = os.environ["SLACK_WEBHOOK_URL"]
DAILY_BUCKET = dt.date.today().isoformat()

# =========================
# Filters
# =========================
INCLUDE_PHRASES = [
    # music/event announces
    "announces tour","announced tour","announce tour","announces dates","announced dates","sets dates","confirms dates",
    "world tour","stadium tour","arena tour",
    "tour dates","dates announced","adds dates","new dates","extra date","second show","adds second night",
    "residency","headline show","headlining show","festival lineup","lineup announced","line-up announced",
    "tickets on sale","ticket pre-sale","presale","pre-sale","on sale",
    # sports fixtures / venues
    "fixture list","fixtures announced","fixtures confirmed","schedule released","schedule announced","match schedule",
    "draw announced","draw made","host city announced","host selected","host city selected",
    "venue change","changed venue","venue confirmed","moved to","relocated","rescheduled","date change",
]
ALWAYS_ALLOW = [
    "olympics","fifa world cup","uefa euro","copa américa","copa america",
    "icc cricket world cup","formula 1","ryder cup","indian wells","super bowl",
]
EXCLUDE_PHRASES = [
    "how to watch","when and where to watch","live streaming","livestream",
    "tv channel","broadcast info","what time is","kick-off time","line-ups",
    "preview","odds","prediction","rumor","rumour","speculation","transfer",
    "injury","sidelined","contract","interview","feature","opinion","column",
    "review","recap","ratings","photo gallery","photos:","fan is visiting","budget",
    "box office","chart","streaming numbers","behind the scenes"
]

ARTISTS = [
    "Beyoncé","Taylor Swift","Adele","Ed Sheeran","Harry Styles","Billie Eilish",
    "Dua Lipa","Ariana Grande","Justin Bieber","Olivia Rodrigo","Lady Gaga","Katy Perry","Shakira",
    "Coldplay","Imagine Dragons","Maroon 5","The Killers","Muse","Foo Fighters",
    "Red Hot Chili Peppers","Metallica","Green Day","U2","Oasis","Blur","Arctic Monkeys",
    "Radiohead","The Rolling Stones","ABBA","Genesis","The Eagles","Fleetwood Mac",
    "Bruce Springsteen","Paul McCartney","Elton John","Billy Joel","Madonna","Celine Dion",
    "Guns N' Roses","Kiss","AC/DC","Pearl Jam","Nirvana","The Who","Bon Jovi","Aerosmith",
    "Def Leppard","Journey","Bad Bunny","Karol G","J Balvin","Maluma","Rosalía","Peso Pluma",
    "Rauw Alejandro","Daddy Yankee","Enrique Iglesias","Luis Miguel","Drake","The Weeknd",
    "Travis Scott","Kendrick Lamar","Kanye West","Nicki Minaj","Doja Cat","Post Malone",
    "Frank Ocean","SZA","BTS","BLACKPINK","SEVENTEEN","Stray Kids","TWICE","NCT","ENHYPEN",
    "TXT","NewJeans","Aespa","ITZY","IVE","LE SSERAFIM","EXO","Garth Brooks","Luke Combs",
    "Morgan Wallen","Chris Stapleton","Carrie Underwood","George Strait","Kacey Musgraves","Dolly Parton"
]

COUNTRIES = [
    "United States","USA","US","UK","United Kingdom","England","Scotland","Wales",
    "Ireland","France","Germany","Spain","Portugal","Italy","Netherlands","Belgium",
    "Sweden","Norway","Denmark","Finland","Poland","Czech Republic","Austria",
    "Switzerland","Greece","Turkey","Russia","Ukraine","Canada","Mexico","Brazil",
    "Argentina","Chile","Colombia","Peru","Japan","South Korea","Korea","China",
    "Hong Kong","Taiwan","Singapore","Malaysia","Thailand","Vietnam","Philippines",
    "India","Pakistan","Bangladesh","Sri Lanka","Australia","New Zealand","South Africa",
    "Nigeria","Kenya","Egypt","Morocco","UAE","Saudi Arabia","Qatar"
]
COUNTRIES_LOWER = [c.lower() for c in COUNTRIES]

SIG_PATTERNS = [
    r"\bfirst (?:time|ever) in (?P<place>[A-Za-z\s]+)",
    r"\bfirst[-\s]?ever\b", r"\bafter (?P<years>\d+)\s+years\b",
    r"\bsince (?:19|20)\d{2}\b", r"\breunion|reunite|original lineup\b",
    r"\bresidency\b", r"\b(stadium|arena) tour\b",
    r"\badds? \d+ (?:new )?dates?\b", r"\bannounces? (?:world )?tour\b",
    r"\bvenue change\b", r"\bchanged venue\b", r"\bmoved to\b",
    r"\brelocated\b", r"\brescheduled\b", r"\bdate change\b",
]
SIG_REGEX = re.compile("|".join(SIG_PATTERNS), re.IGNORECASE)

WEAK_EVENT_WORDS = ["tour","concert","show","dates","tickets","presale","pre-sale","fixture","match","venue","lineup","line-up"]

# =========================
# Dedupe storage
# =========================
SEEN_PATH = "seen.json"
seen = {}
if os.path.exists(SEEN_PATH):
    try: seen = json.load(open(SEEN_PATH))
    except: seen = {}
if DAILY_BUCKET not in seen:
    seen[DAILY_BUCKET] = {"titles": [], "artists": []}
titles_seen = set(seen[DAILY_BUCKET].get("titles", []))
artists_seen = set(seen[DAILY_BUCKET].get("artists", []))
event_keys_list = seen.get("event_keys", [])
cutoff = dt.date.today() - dt.timedelta(days=DEDUP_DAYS-1)
event_keys_list = [ek for ek in event_keys_list if ek.get("date") >= cutoff.isoformat()]
recent_event_keys = set(ek["key"] for ek in event_keys_list)

# =========================
# Helpers
# =========================
def canonical_key(title): return hashlib.sha256(title.lower().encode()).hexdigest()[:16]
def any_in(text, words): return any(w in text.lower() for w in words)
def entry_datetime(e):
    for fld in ("published","updated","pubDate"):
        val = getattr(e,fld,"") or (e.get(fld,"") if isinstance(e,dict) else "")
        if val:
            try: return parsedate_to_datetime(val)
            except: pass
    for fld in ("published_parsed","updated_parsed"):
        val = getattr(e,fld,None)
        if val:
            try: return dt.datetime(*val[:6], tzinfo=dt.timezone.utc)
            except: pass
    return None
def is_recent(e):
    d=entry_datetime(e)
    if not d: return False
    if not d.tzinfo: d=d.replace(tzinfo=dt.timezone.utc)
    return (dt.datetime.now(dt.timezone.utc)-d).total_seconds() <= MAX_AGE_HOURS*3600
def artist_event_match(text: str) -> bool:
    t = text.lower()
    if any(a.lower() in t for a in ARTISTS):
        if any(w in t for w in WEAK_EVENT_WORDS):
            return True
    return False
def is_relevant(text):
    if any_in(text,EXCLUDE_PHRASES): return False
    if any_in(text,ALWAYS_ALLOW): return True
    if any_in(text,INCLUDE_PHRASES): return True
    return artist_event_match(text)
def detect_country(text):
    t=text.lower()
    for c,cl in zip(COUNTRIES,COUNTRIES_LOWER):
        if cl in t: return c
    m=re.search(r"\bin\s+([A-Z][A-Za-z\s]+)\b",text); return m.group(1) if m else ""
def detect_signal(text):
    m=SIG_REGEX.search(text)
    if not m: return ""
    return m.group(0).replace("firstever","first-ever").strip().capitalize()
def detect_artist(text):
    t=text.lower()
    for a in ARTISTS:
        if a.lower() in t: return a
    return ""
def signal_category(text):
    t=text.lower()
    if any(p in t for p in ["venue change","changed venue","moved to","relocated","rescheduled","date change"]): return "VENUE_CHANGE"
    if any(p in t for p in ["fixture","schedule released","fixtures announced","draw announced","draw made"]): return "SCHEDULE"
    if any(p in t for p in ["tickets on sale","pre-sale","presale","on sale"]): return "TICKETS"
    if any(p in t for p in ["tour dates","adds dates","new dates","extra date","second show","adds second night"]): return "DATES"
    if any(p in t for p in ["announces tour","announced tour","world tour","stadium tour","arena tour"]): return "TOUR"
    if any(p in t for p in ["olympics","fifa world cup","uefa euro","super bowl","icc cricket world cup"]): return "MEGA"
    return "GEN"
def score_item(title,summary):
    t=(title+" "+summary).lower(); s=0
    for k in ["announces tour","tour dates","world tour","stadium tour","residency",
              "adds dates","tickets on sale","fixture","fixtures announced","schedule released","draw announced",
              "venue change","relocated","moved to","rescheduled"]:
        if k in t: s+=4
    if any(a.lower() in t for a in ARTISTS): s+=3
    if any(m in t for m in ALWAYS_ALLOW): s+=5
    if any(c in t for c in COUNTRIES_LOWER): s+=1
    return s
def post_to_slack(title,link,source,country="",signal=""):
    payload={
        "title":title,"url":link,"source":source,"country":country,"signal":signal,
        "text":f"🎟️ {title}\n• Source: {source} • Country: {country}\n• {signal}\n🔗 {link}"
    }
    r=requests.post(SLACK_WEBHOOK,json=payload,timeout=15)
    print("Slack:",r.status_code,r.text[:120])

def make_event_key(artist,country,category,title_key=None):
    if not artist:
        return f"{(country or 'UNK').lower()}|{category}|{title_key or 'NA'}"
    return f"{artist.lower()}|{(country or 'UNK').lower()}|{category}"

# =========================
# Collect → Filter → Score
# =========================
def run():
    feeds = get_all_feeds()
    candidates=[]
    for url in feeds:
        try: feed=feedparser.parse(url)
        except Exception as e:
            print("Feed error:", url, e); continue
        for e in feed.entries[:ENTRIES_PER_FEED]:
            if not is_recent(e): continue
            title=getattr(e,"title","") or ""; link=getattr(e,"link","") or ""
            summary=getattr(e,"summary","") or ""; source=getattr(e,"source",{}).get("title","") or url
            if not title or not link: continue
            blob=f"{title} {summary}"
            if not is_relevant(blob): continue
            candidates.append({
                "title":title,"url":link,"source":source,"blob":blob,
                "score":score_item(title,summary),"artist":detect_artist(blob),
                "country":detect_country(blob),"signal":detect_signal(blob),
                "category":signal_category(blob),"title_key":canonical_key(title)
            })

    # Dedupe + Rank
    final=[]
    for c in sorted(candidates,key=lambda x:(-x["score"],x["title"])):
        if c["title_key"] in titles_seen: continue
        if c["artist"] and c["artist"] in artists_seen: continue
        ek=make_event_key(c["artist"],c["country"],c["category"],c["title_key"])
        if ek in recent_event_keys: continue
        final.append(c)
        titles_seen.add(c["title_key"])
        if c["artist"]: artists_seen.add(c["artist"])
        recent_event_keys.add(ek); event_keys_list.append({"date":DAILY_BUCKET,"key":ek})
        if len(final)>=MAX_POSTS: break

    # Post
    for c in final:
        try:
            post_to_slack(c["title"],c["url"],c["source"],c["country"],c["signal"])
            time.sleep(1)
        except Exception as e:
            print("Post error:",e)

    # Save state
    seen[DAILY_BUCKET]={"titles":list(titles_seen),"artists":list(artists_seen)}
    seen["event_keys"]=event_keys_list
    with open(SEEN_PATH,"w") as f: json.dump(seen,f)
    print(f"checked={len(candidates)} posted={len(final)}")

if __name__ == "__main__":
    run()
