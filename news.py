from dataclasses import dataclass
from email.utils import parsedate_to_datetime
import urllib.request
import xml.etree.ElementTree as ET

@dataclass
class Headline:
    source: str
    title: str
    link: str
    published: str

FEEDS = [
    ("Federal Reserve - Monetary Policy","https://www.federalreserve.gov/feeds/press_monetary.xml"),
    ("Federal Reserve - All Press Releases","https://www.federalreserve.gov/feeds/press_all.xml"),
    ("BLS - CPI","https://www.bls.gov/feed/cpi.rss"),
    ("BLS - Employment Situation","https://www.bls.gov/feed/empsit.rss"),
]

KEYWORDS = ("federal reserve","fomc","monetary","rate","inflation","consumer price","employment","payroll","unemployment","producer price","jobs","labor")

def _fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent":"Pablo-XAU-AI/3.0"})
    with urllib.request.urlopen(req, timeout=12) as r:
        return r.read()

def get_official_headlines(limit=12):
    items = []
    for source,url in FEEDS:
        try:
            root = ET.fromstring(_fetch(url))
        except Exception:
            continue
        for item in root.findall(".//item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            pub = (item.findtext("pubDate") or "").strip()
            if "All Press Releases" in source and not any(k in title.lower() for k in KEYWORDS):
                continue
            items.append(Headline(source,title,link,pub))

    unique = {x.title:x for x in items}
    def ts(x):
        try:
            return parsedate_to_datetime(x.published).timestamp()
        except Exception:
            return 0

    return sorted(unique.values(), key=ts, reverse=True)[:limit]
