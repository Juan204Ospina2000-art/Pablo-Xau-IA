from __future__ import annotations
from dataclasses import dataclass
import json
import urllib.parse
import urllib.request
from typing import List

BASE = "https://api.gdeltproject.org/api/v2/doc/doc"

@dataclass
class GlobalHeadline:
    title: str
    url: str
    domain: str
    sourcecountry: str
    seendate: str
    tone: str
    gold_bias: int
    explanation: str

BULLISH = {
    "rate cut": 2, "cuts rates": 2, "dovish": 2, "weak dollar": 2,
    "dollar falls": 1, "yields fall": 2, "yield falls": 2, "recession": 1,
    "war": 1, "sanctions": 1, "geopolitical tensions": 2, "escalation": 1,
    "safe haven": 2, "inflation rises": 1, "inflation accelerates": 1,
}
BEARISH = {
    "rate hike": -2, "raises rates": -2, "hawkish": -2, "strong dollar": -2,
    "dollar rises": -1, "yields rise": -2, "yield rises": -2, "ceasefire": -1,
    "inflation cools": -1, "inflation falls": -1, "soft landing": -1,
}

def classify_title(title):
    low = title.lower()
    score = 0
    hits = []
    for k,v in BULLISH.items():
        if k in low:
            score += v; hits.append(k)
    for k,v in BEARISH.items():
        if k in low:
            score += v; hits.append(k)
    if score > 0:
        return min(3,score), "Potencialmente favorable para oro: " + ", ".join(hits[:3])
    if score < 0:
        return max(-3,score), "Potencialmente desfavorable para oro: " + ", ".join(hits[:3])
    return 0, "Sin sesgo claro por palabras clave"

def fetch_global_gold_news(maxrecords=25, timespan="6h"):
    query = '("gold" OR XAUUSD OR "Federal Reserve" OR inflation OR "US dollar" OR Treasury OR geopolitical)'
    params = {
        "query": query,
        "mode": "artlist",
        "maxrecords": maxrecords,
        "timespan": timespan,
        "sort": "datedesc",
        "format": "json",
    }
    url = BASE + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent":"Pablo-XAU-AI/4.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            payload = json.loads(r.read().decode("utf-8", errors="replace"))
    except Exception:
        return []

    articles = payload.get("articles", []) if isinstance(payload, dict) else []
    out = []
    for a in articles:
        title = (a.get("title") or "").strip()
        if not title:
            continue
        bias, explanation = classify_title(title)
        out.append(GlobalHeadline(
            title=title,
            url=a.get("url",""),
            domain=a.get("domain",""),
            sourcecountry=a.get("sourcecountry",""),
            seendate=a.get("seendate",""),
            tone=str(a.get("tone","")),
            gold_bias=bias,
            explanation=explanation,
        ))
    return out

def aggregate_news_bias(items):
    if not items:
        return 0
    raw = sum(x.gold_bias for x in items[:15])
    if raw >= 5: return 3
    if raw >= 2: return 2
    if raw <= -5: return -3
    if raw <= -2: return -2
    return 0
