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
        out.append(value * k + out[-1] * (1 - k))
    return out

def analyze_timeframe(timeframe: str, candles: List[Candle]) -> TFAnalysis:
    if len(candles) < 30:
        raise ValueError(f"No hay suficientes velas para analizar {timeframe}.")

    closes = [c.close for c in candles]
    e20 = ema(closes, 20)
    e50 = ema(closes, 50)

    last = candles[-1]
    prev = candles[-2]

    if last.close > e20[-1] > e50[-1]:
        trend = "ALCISTA"
    elif last.close < e20[-1] < e50[-1]:
        trend = "BAJISTA"
    else:
        trend = "NEUTRAL"

    # Simple market structure using two rolling windows.
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

    # Basic liquidity sweep heuristic:
    # latest candle takes prior 20-bar extreme but closes back inside.
    prior20 = candles[-21:-1]
    prior_high = max(c.high for c in prior20)
    prior_low = min(c.low for c in prior20)

    if last.high > prior_high and last.close < prior_high:
        sweep = "SWEEP HIGH"
    elif last.low < prior_low and last.close > prior_low:
        sweep = "SWEEP LOW"
    else:
        sweep = "NINGUNO"

    body_now = abs(last.close - last.open)
    avg_body = mean(abs(c.close - c.open) for c in candles[-20:-1])
    if avg_body and body_now >= avg_body * 1.5:
        momentum = "FUERTE"
    elif avg_body and body_now <= avg_body * 0.6:
        momentum = "DÉBIL"
    else:
        momentum = "NORMAL"

    return TFAnalysis(
        timeframe=timeframe,
        trend=trend,
        structure=structure,
        last_close=last.close,
        recent_high=rh,
        recent_low=rl,
        sweep=sweep,
        momentum=momentum,
    )

def analyze_market(candles_by_tf: Dict[str, List[Candle]]):
    return {
        tf: analyze_timeframe(tf, candles)
        for tf, candles in candles_by_tf.items()
    }

def derive_bias(analyses):
    weights = {"M1": 1, "M5": 2, "M15": 3, "H1": 4, "H4": 5}
    score = 0

    for tf, a in analyses.items():
        w = weights.get(tf, 1)
        if a.trend == "ALCISTA":
            score += w
        elif a.trend == "BAJISTA":
            score -= w

    if score >= 6:
        return "ALCISTA", score
    if score <= -6:
        return "BAJISTA", score
    return "NEUTRAL", score

def detect_live_signal(analyses):
    """
    V2: detector deliberadamente conservador.
    H1/H4 dan contexto; M5/M15 deben confirmar.
    """
    bias, score = derive_bias(analyses)
    m5 = analyses["M5"]
    m15 = analyses["M15"]
    h1 = analyses["H1"]
    h4 = analyses["H4"]

    reasons = []

    if bias == "ALCISTA":
        confirm = (
            m5.structure == "HH/HL"
            and m15.trend == "ALCISTA"
            and h1.trend != "BAJISTA"
            and h4.trend != "BAJISTA"
        )
        sweep_ok = m5.sweep in ("SWEEP LOW", "NINGUNO")
        if confirm and sweep_ok:
            reasons.extend([
                "Sesgo multi-timeframe alcista",
                "M5 en estructura HH/HL",
                "M15 confirma dirección",
            ])
            if m5.sweep == "SWEEP LOW":
                reasons.append("Sweep de mínimos detectado en M5")
            return "BUY CANDIDATE", bias, score, reasons

    if bias == "BAJISTA":
        confirm = (
            m5.structure == "LH/LL"
            and m15.trend == "BAJISTA"
            and h1.trend != "ALCISTA"
            and h4.trend != "ALCISTA"
        )
        sweep_ok = m5.sweep in ("SWEEP HIGH", "NINGUNO")
        if confirm and sweep_ok:
            reasons.extend([
                "Sesgo multi-timeframe bajista",
                "M5 en estructura LH/LL",
                "M15 confirma dirección",
            ])
            if m5.sweep == "SWEEP HIGH":
                reasons.append("Sweep de máximos detectado en M5")
            return "SELL CANDIDATE", bias, score, reasons

    reasons.append("Faltan confluencias suficientes para entrada sniper")
    return "WAIT", bias, score, reasons
