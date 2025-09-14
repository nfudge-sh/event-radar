import json, time, hashlib, requests, feedparser, os, re

# --- CONFIG ---
FEEDS = [
    "https://www.billboard.com/feed/",
    "https://www.pollstar.com/feed",
    "https://www.fifa.com/rss-feeds/index.xml",
    "https://www.uefa.com/rssfeed/uefaeuro.rss",
    "https://espnpressroom.com/us/feed/",
]

KEYS = [
    "tour","concert","residency","reunion","stadium","arena",
    "adds dates","announces dates","first time","since 20","since 19"
]

ARTISTS = [
    "Beyoncé","Taylor Swift","Coldplay","Bad Bunny","Karol G",
    "Drake","Adele","Ed Sheeran","Billie Eilish","The Weeknd",
    "BTS","BLACKPINK","Harry Styles"
]

SLACK_WEBHOOK = os.environ["SLACK_WEBHOOK_URL"]  # will come from GitHub Secrets

# --- DEDUPE CACHE ---
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

def is_hit(text: str) -> bool:
    t = text.lower()
    if any(a.lower() in t for a in ARTISTS): return True
    if any(k in t for k in KEYS): return True
    return False

def post_to_slack(title, link, source):
    txt = f"🎟️ {title}\n• Source: {source}\n🔗 {link}"
    requests.post(SLACK_WEBHOOK, json={"text": txt}, timeout=15)

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
        if not is_hit(f"{title} {summary}"):
            continue

        key = canonical_key(title)
        if key in seen:
            continue

        try:
            post_to_slack(title, link, source)
            seen.add(key); posted += 1
            time.sleep(1)  # avoid Slack spam
        except Exception:
            continue

# keep last 5000 dedupe keys
json.dump(list(seen)[-5000:], open(SEEN_PATH, "w"))
print(f"posted={posted}")
