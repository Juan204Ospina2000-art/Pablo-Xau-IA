from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta, date, time
from zoneinfo import ZoneInfo
import urllib.request

NY = ZoneInfo("America/New_York")
MADRID = ZoneInfo("Europe/Madrid")
BLS_ICS_URL = "https://www.bls.gov/schedule/news_release/bls.ics"

HIGH_IMPACT_KEYWORDS = {
    "consumer price index": "CPI",
    "employment situation": "NFP / Employment Situation",
    "producer price index": "PPI",
    "job openings and labor turnover": "JOLTS",
    "employment cost index": "ECI",
    "import and export price": "Import/Export Prices",
    "real earnings": "Real Earnings",
}

FOMC_FINAL_DAYS = [
    date(2026,1,28), date(2026,3,18), date(2026,4,29), date(2026,6,17),
    date(2026,7,29), date(2026,9,16), date(2026,10,28), date(2026,12,9),
    date(2027,1,27), date(2027,3,17), date(2027,4,28), date(2027,6,9),
    date(2027,7,28), date(2027,9,15), date(2027,10,27), date(2027,12,8),
]

@dataclass
class MacroEvent:
    title: str
    datetime_ny: datetime
    impact: str
    source: str

    @property
    def datetime_madrid(self):
        return self.datetime_ny.astimezone(MADRID)

@dataclass
class MacroRisk:
    level: str
    blocked: bool
    nearest_event: MacroEvent | None
    minutes_to_event: int | None
    message: str

def _fetch_text(url):
    req = urllib.request.Request(url, headers={"User-Agent":"Pablo-XAU-AI/3.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read().decode("utf-8", errors="replace")

def _unfold_ics(text):
    lines = text.replace("\r\n","\n").split("\n")
    out = []
    for line in lines:
        if line.startswith((" ","\t")) and out:
            out[-1] += line[1:]
        else:
            out.append(line)
    return out

def _parse_dt(raw):
    raw = raw.strip()
    for fmt in ("%Y%m%dT%H%M%S","%Y%m%dT%H%M","%Y%m%d"):
        try:
            v = datetime.strptime(raw.rstrip("Z"), fmt)
            if raw.endswith("Z"):
                return v.replace(tzinfo=ZoneInfo("UTC")).astimezone(NY)
            return v.replace(tzinfo=NY)
        except ValueError:
            pass
    return None

def get_bls_events(days_ahead=30, now=None):
    now = now or datetime.now(NY)
    end = now + timedelta(days=days_ahead)
    try:
        text = _fetch_text(BLS_ICS_URL)
    except Exception:
        return []

    events = []
    current = {}

    def flush():
        if not current:
            return
        title = current.get("SUMMARY","")
        dt = current.get("DTSTART")
        if not title or not dt:
            return
        low = title.lower()
        matched = next((display for key,display in HIGH_IMPACT_KEYWORDS.items() if key in low), None)
        if matched and now - timedelta(hours=2) <= dt <= end:
            events.append(MacroEvent(matched, dt, "HIGH", "BLS"))

    for line in _unfold_ics(text):
        if line == "BEGIN:VEVENT":
            current = {}
        elif line == "END:VEVENT":
            flush()
            current = {}
        elif line.startswith("SUMMARY:"):
            current["SUMMARY"] = line.split(":",1)[1].replace("\\,",",")
        elif line.startswith("DTSTART"):
            dt = _parse_dt(line.split(":",1)[1])
            if dt:
                current["DTSTART"] = dt

    return sorted(events, key=lambda e:e.datetime_ny)

def get_fomc_events(days_ahead=90, now=None):
    now = now or datetime.now(NY)
    end = now + timedelta(days=days_ahead)
    out = []
    for d in FOMC_FINAL_DAYS:
        dt = datetime.combine(d, time(14,0), tzinfo=NY)
        if now - timedelta(hours=6) <= dt <= end:
            out.append(MacroEvent("FOMC Statement", dt, "EXTREME", "Federal Reserve"))
            out.append(MacroEvent("FOMC Press Conference", dt+timedelta(minutes=30), "EXTREME", "Federal Reserve"))
    return sorted(out, key=lambda e:e.datetime_ny)

def get_macro_events(days_ahead=30, now=None):
    now = now or datetime.now(NY)
    events = get_bls_events(days_ahead, now) + get_fomc_events(max(days_ahead,90), now)
    unique = {(e.title,e.datetime_ny.isoformat()):e for e in events}
    return sorted(unique.values(), key=lambda e:e.datetime_ny)

def assess_macro_risk(events, now=None):
    now = now or datetime.now(NY)
    if not events:
        return MacroRisk("UNKNOWN", False, None, None, "No se pudo confirmar un evento macro próximo.")

    nearest = min(events, key=lambda e:abs((e.datetime_ny-now).total_seconds()))
    minutes = int((nearest.datetime_ny-now).total_seconds()/60)

    if nearest.impact == "EXTREME":
        if -90 <= minutes <= 120:
            return MacroRisk("EXTREME", True, nearest, minutes, "FOMC en ventana crítica: NO TRADE.")
        if -360 <= minutes < -90 or 120 < minutes <= 360:
            return MacroRisk("HIGH", False, nearest, minutes, "Sesión FOMC: exigir confirmación extra.")

    if nearest.impact == "HIGH":
        if -30 <= minutes <= 45:
            return MacroRisk("HIGH", True, nearest, minutes, f"{nearest.title} en ventana crítica: NO TRADE.")
        if -120 <= minutes < -30 or 45 < minutes <= 120:
            return MacroRisk("MEDIUM", False, nearest, minutes, f"{nearest.title} cercano: exigir confirmación extra.")

    return MacroRisk("LOW", False, nearest, minutes, "Sin evento macro crítico en la ventana inmediata.")
