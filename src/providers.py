# providers.py
# Central place to manage official RSS feeds (no Google News).
# Add/remove feeds here as needed.

# ESPN RSS (you asked for this explicitly)
ESPN_RSS = "https://www.espn.com/espn/rss/news"

MUSIC_TRADE = [
    "https://www.billboard.com/feed/",
    "https://www.pollstar.com/feed",
    "https://variety.com/feed/",
    "https://www.rollingstone.com/feed/",
    "https://consequence.net/feed/",
    "https://www.nme.com/feed",
    "https://www.spin.com/feed/",
    "https://www.vulture.com/rss/music.xml",
    "https://pitchfork.com/feed/",
    "https://www.stereogum.com/feed/",
    "https://www.jambase.com/feed",
    "https://www.udiscovermusic.com/feed/",
    "https://www.kerrang.com/feed.xml",
]

TICKETING = [
    "https://blog.ticketmaster.com/feed/",
    "https://www.livenationentertainment.com/feed/",
    "https://www.ticketmaster.co.uk/blog/feed/",
    "https://blog.ticketmaster.com.au/feed/",
    "https://www.ticketmaster.de/magazin/feed/",
    "https://www.aegpresents.co.uk/feed/",
]

FESTIVALS = [
    "https://www.coachella.com/feed/",
    "https://www.glastonburyfestivals.co.uk/feed/",
    "https://www.lollapalooza.com/feed/",
    "https://www.rockwerchter.be/en/rss",
    "https://primaverasound.com/en/rss",
    "https://readingandleedsfestival.com/feed/",
    "https://splendourinthegrass.com/feed/",
    "https://fujirockfestival.com/feed/",
]

VENUES = [
    "https://www.wembleystadium.com/rss",
    "https://www.theo2.co.uk/rss",
    "https://www.sofistadium.com/feed/",
    "https://accorarena.com/en/feed/",
    "https://www.ao-arena.com/rss",
    "https://www.3arena.ie/feed/",
    "https://www.rodlaverarena.com.au/feed/",
    "https://www.scotiabankarena.com/feed/",
    "https://www.ssearena.co.uk/rss",
    "https://www.etihadarena.ae/en/media-centre/rss",
    "https://www.spark-arena.co.nz/feed/",
]

SPORTS_WIRES = [
    "https://feeds.bbci.co.uk/sport/rss.xml",
    ESPN_RSS,
    "https://espnpressroom.com/us/feed/",
    "https://www.reuters.com/rssFeed/sportsNews",
]

FEDERATIONS_COMPETITIONS = [
    # FIFA / UEFA / Olympics / ICC / F1
    "https://www.fifa.com/rss-feeds/index.xml",
    "https://www.uefa.com/rssfeed/uefachampionsleague.rss",
    "https://www.uefa.com/rssfeed/uefaeuropaleague.rss",
    "https://www.uefa.com/rssfeed/uefaconferenceleague.rss",
    "https://www.uefa.com/rssfeed/uefaeuro.rss",
    "https://www.uefa.com/rssfeed/uefanationsleague.rss",
    "https://www.olympics.com/en/news/rss",
    "https://www.icc-cricket.com/rss/news",
    "https://www.formula1.com/content/fom-website/en/latest/all.xml",
]

LEAGUES = [
    # You listed these codes; these feeds map closely:
    # PL (Premier League)
    "https://www.premierleague.com/news.rss",
    # BL1 (Bundesliga)
    "https://www.bundesliga.com/en/bundesliga/rss",
    # SA (Serie A)
    "https://www.legaseriea.it/en/rss",
    # FL1 (Ligue 1)
    "https://ligue1.com/rss",
    # PD (LaLiga / Primera División)
    "https://www.laliga.com/rss",
    # DED (Eredivisie)
    "https://eredivisie.nl/feed/",
    # PPL (Primeira Liga)
    "https://www.ligaportugal.pt/en/media/rss",
    # ELC (Championship) – via EFL
    "https://www.efl.com/rss/news.xml",
    # BSA (Brasileirão Série A) – via CBF
    "https://www.cbf.com.br/rss",
    # MLS (bonus global relevance)
    "https://www.mlssoccer.com/feeds/rss/news.xml",
]

# Compose the full list
def get_all_feeds() -> list[str]:
    return (
        MUSIC_TRADE
        + TICKETING
        + FESTIVALS
        + VENUES
        + SPORTS_WIRES
        + FEDERATIONS_COMPETITIONS
        + LEAGUES
    )
