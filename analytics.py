from __future__ import annotations
from dataclasses import dataclass
from statistics import mean
from typing import List, Dict, Optional
from market_data import Candle

@dataclass
class AdvancedTF:
    timeframe: str
    atr: float
    atr_pct: float
    ema20: float
    ema50: float
    ema_slope: float
    volatility: str
    regime: str
    range_high: float
    range_low: float

def ema(values, period):
    if not values:
        return []
    k = 2 / (period + 1)
    out = [values[0]]
    for v in values[1:]:
        out.append(v * k + out[-1] * (1-k))
    return out

def true_ranges(candles: List[Candle]):
    out = []
    prev_close = None
    for c in candles:
        if prev_close is None:
            tr = c.high - c.low
        else:
            tr = max(c.high-c.low, abs(c.high-prev_close), abs(c.low-prev_close))
        out.append(tr)
        prev_close = c.close
    return out

def atr(candles: List[Candle], period=14):
    trs = true_ranges(candles)
    if len(trs) < period:
        return mean(trs) if trs else 0.0
    return mean(trs[-period:])

def analyze_advanced(timeframe: str, candles: List[Candle]) -> AdvancedTF:
    closes = [c.close for c in candles]
    e20 = ema(closes, 20)
    e50 = ema(closes, 50)
    current_atr = atr(candles, 14)
    last = candles[-1].close
    atr_pct = (current_atr / last * 100) if last else 0.0
    slope = e20[-1] - e20[-5] if len(e20) >= 5 else 0.0

    recent_atrs = []
    if len(candles) >= 80:
        for i in range(40, len(candles)+1):
            recent_atrs.append(atr(candles[:i], 14))
    benchmark = mean(recent_atrs[-50:]) if recent_atrs else current_atr

    if benchmark and current_atr > benchmark * 1.35:
        volatility = "ALTA"
    elif benchmark and current_atr < benchmark * 0.75:
        volatility = "BAJA"
    else:
        volatility = "NORMAL"

    ema_gap = abs(e20[-1] - e50[-1])
    if current_atr and ema_gap > current_atr * 0.7 and abs(slope) > current_atr * 0.08:
        regime = "TENDENCIA"
    elif current_atr and ema_gap < current_atr * 0.35:
        regime = "RANGO"
    else:
        regime = "TRANSICIÓN"

    recent = candles[-30:]
    return AdvancedTF(
        timeframe=timeframe,
        atr=round(current_atr, 3),
        atr_pct=round(atr_pct, 4),
        ema20=round(e20[-1], 3),
        ema50=round(e50[-1], 3),
        ema_slope=round(slope, 3),
        volatility=volatility,
        regime=regime,
        range_high=round(max(c.high for c in recent), 3),
        range_low=round(min(c.low for c in recent), 3),
    )

def analyze_all_advanced(candles_by_tf: Dict[str, List[Candle]]):
    return {tf: analyze_advanced(tf, candles) for tf, candles in candles_by_tf.items()}

def session_context(now_ny):
    h = now_ny.hour + now_ny.minute/60
    if 2 <= h < 5:
        return "LONDRES", "Ventana activa de Londres"
    if 7 <= h < 8.5:
        return "PRE-NY", "Preparación antes de Nueva York"
    if 8.5 <= h < 11:
        return "NUEVA YORK", "Ventana principal de Nueva York"
    if 11 <= h < 13:
        return "NY MEDIA SESIÓN", "Liquidez suele reducirse respecto a la apertura"
    return "FUERA DE KILL ZONE", "Esperar selectivamente setups de alta calidad"

def confluence_score(basic, advanced, macro_risk, global_news_score=0):
    """
    Score interno 0-100. No equivale a probabilidad de ganar.
    """
    score = 50
    reasons = []

    h4, h1, m15, m5 = basic["H4"], basic["H1"], basic["M15"], basic["M5"]
    a5, a15 = advanced["M5"], advanced["M15"]

    directions = [x.trend for x in (h4,h1,m15,m5)]
    bullish = directions.count("ALCISTA")
    bearish = directions.count("BAJISTA")
    if max(bullish,bearish) >= 3:
        score += 12; reasons.append("+12 alineación multi-timeframe")
    elif bullish >= 2 and bearish >= 2:
        score -= 8; reasons.append("-8 conflicto multi-timeframe")

    if m5.structure in ("HH/HL","LH/LL"):
        score += 8; reasons.append("+8 estructura M5 limpia")
    else:
        score -= 5; reasons.append("-5 estructura M5 mixta")

    if m5.sweep != "NINGUNO":
        score += 10; reasons.append("+10 sweep M5")
    if m15.sweep != "NINGUNO":
        score += 6; reasons.append("+6 sweep M15")

    if a5.regime == "TENDENCIA" and a15.regime == "TENDENCIA":
        score += 7; reasons.append("+7 régimen tendencial")
    elif a5.regime == "RANGO":
        score -= 7; reasons.append("-7 M5 en rango")

    if a5.volatility == "ALTA":
        score -= 4; reasons.append("-4 volatilidad M5 alta")
    elif a5.volatility == "NORMAL":
        score += 3; reasons.append("+3 volatilidad normal")

    if macro_risk:
        if macro_risk.blocked:
            score -= 35; reasons.append("-35 bloqueo macro")
        elif macro_risk.level == "HIGH":
            score -= 18; reasons.append("-18 riesgo macro alto")
        elif macro_risk.level == "MEDIUM":
            score -= 10; reasons.append("-10 riesgo macro medio")
        elif macro_risk.level == "LOW":
            score += 4; reasons.append("+4 macro limpio")

    if global_news_score >= 2:
        score += 4; reasons.append("+4 noticias apoyan sesgo oro")
    elif global_news_score <= -2:
        score -= 4; reasons.append("-4 noticias presionan oro")

    return max(0, min(100, int(score))), reasons
