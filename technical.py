from dataclasses import dataclass
from statistics import mean
from typing import Dict, List
from market_data import Candle

@dataclass
class TFAnalysis:
    timeframe: str
    trend: str
    structure: str
    last_close: float
    recent_high: float
    recent_low: float
    sweep: str
    momentum: str

def ema(values, period):
    if not values:
        return []
    k = 2 / (period + 1)
    out = [values[0]]
    for value in values[1:]:
        out.append(value * k + out[-1] * (1-k))
    return out

def analyze_timeframe(timeframe: str, candles: List[Candle]) -> TFAnalysis:
    if len(candles) < 30:
        raise ValueError(f"No hay suficientes velas para analizar {timeframe}.")

    closes = [c.close for c in candles]
    e20 = ema(closes, 20)
    e50 = ema(closes, 50)
    last = candles[-1]

    if last.close > e20[-1] > e50[-1]:
        trend = "ALCISTA"
    elif last.close < e20[-1] < e50[-1]:
        trend = "BAJISTA"
    else:
        trend = "NEUTRAL"

    recent = candles[-10:]
    prior = candles[-20:-10]
    rh = max(c.high for c in recent)
    rl = min(c.low for c in recent)
    ph = max(c.high for c in prior)
    pl = min(c.low for c in prior)

    if rh > ph and rl > pl:
        structure = "HH/HL"
    elif rh < ph and rl < pl:
        structure = "LH/LL"
    else:
        structure = "RANGO/MIXTA"

    prior20 = candles[-21:-1]
    prior_high = max(c.high for c in prior20)
    prior_low = min(c.low for c in prior20)

    if last.high > prior_high and last.close < prior_high:
        sweep = "SWEEP HIGH"
    elif last.low < prior_low and last.close > prior_low:
        sweep = "SWEEP LOW"
    else:
        sweep = "NINGUNO"

    body_now = abs(last.close-last.open)
    avg_body = mean(abs(c.close-c.open) for c in candles[-20:-1])
    if avg_body and body_now >= avg_body*1.5:
        momentum = "FUERTE"
    elif avg_body and body_now <= avg_body*0.6:
        momentum = "DÉBIL"
    else:
        momentum = "NORMAL"

    return TFAnalysis(timeframe, trend, structure, last.close, rh, rl, sweep, momentum)

def analyze_market(candles_by_tf: Dict[str, List[Candle]]):
    return {tf: analyze_timeframe(tf, candles) for tf, candles in candles_by_tf.items()}

def derive_bias(analyses):
    weights = {"M1":1, "M5":3, "M15":4, "H1":3, "H4":2}
    score = 0
    for tf,a in analyses.items():
        w = weights.get(tf,1)
        if a.trend == "ALCISTA":
            score += w
        elif a.trend == "BAJISTA":
            score -= w

    if score >= 4:
        return "ALCISTA", score
    if score <= -4:
        return "BAJISTA", score
    return "NEUTRAL", score

def detect_live_signal(analyses):
    """
    V4.3 BALANCED:
    Prioriza M5/M15 para no llegar tarde.
    H1/H4 aportan contexto, pero ya no tienen veto automático salvo oposición fuerte.
    """
    bias, score = derive_bias(analyses)
    m5 = analyses["M5"]
    m15 = analyses["M15"]
    h1 = analyses["H1"]
    h4 = analyses["H4"]

    reasons = []

    # BUY
    buy_points = 0
    if m5.structure == "HH/HL":
        buy_points += 3; reasons.append("M5 estructura alcista")
    if m15.trend == "ALCISTA":
        buy_points += 2; reasons.append("M15 alcista")
    if m5.trend == "ALCISTA":
        buy_points += 2; reasons.append("M5 alcista")
    if m5.sweep == "SWEEP LOW":
        buy_points += 3; reasons.append("Sweep de mínimos M5")
    if m15.sweep == "SWEEP LOW":
        buy_points += 2; reasons.append("Sweep de mínimos M15")
    if m5.momentum == "FUERTE":
        buy_points += 1; reasons.append("Momentum M5 fuerte")
    if h1.trend == "ALCISTA":
        buy_points += 1
    if h4.trend == "ALCISTA":
        buy_points += 1
    if h1.trend == "BAJISTA" and h4.trend == "BAJISTA":
        buy_points -= 4

    # SELL
    sell_reasons = []
    sell_points = 0
    if m5.structure == "LH/LL":
        sell_points += 3; sell_reasons.append("M5 estructura bajista")
    if m15.trend == "BAJISTA":
        sell_points += 2; sell_reasons.append("M15 bajista")
    if m5.trend == "BAJISTA":
        sell_points += 2; sell_reasons.append("M5 bajista")
    if m5.sweep == "SWEEP HIGH":
        sell_points += 3; sell_reasons.append("Sweep de máximos M5")
    if m15.sweep == "SWEEP HIGH":
        sell_points += 2; sell_reasons.append("Sweep de máximos M15")
    if m5.momentum == "FUERTE":
        sell_points += 1; sell_reasons.append("Momentum M5 fuerte")
    if h1.trend == "BAJISTA":
        sell_points += 1
    if h4.trend == "BAJISTA":
        sell_points += 1
    if h1.trend == "ALCISTA" and h4.trend == "ALCISTA":
        sell_points -= 4

    # Require clear directional edge.
    if buy_points >= 8 and buy_points >= sell_points + 3:
        reasons.append(f"Score direccional BUY {buy_points}")
        return "BUY READY", "ALCISTA", buy_points, reasons

    if sell_points >= 8 and sell_points >= buy_points + 3:
        sell_reasons.append(f"Score direccional SELL {sell_points}")
        return "SELL READY", "BAJISTA", -sell_points, sell_reasons

    if buy_points >= 6 and buy_points > sell_points:
        reasons.append(f"Setup BUY naciendo ({buy_points})")
        return "BUY WATCH", "ALCISTA", buy_points, reasons

    if sell_points >= 6 and sell_points > buy_points:
        sell_reasons.append(f"Setup SELL naciendo ({sell_points})")
        return "SELL WATCH", "BAJISTA", -sell_points, sell_reasons

    return "WAIT", bias, score, ["No hay ventaja direccional suficiente todavía"]
