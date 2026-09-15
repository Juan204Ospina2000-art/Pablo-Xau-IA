from market_data import Candle
from technical import analyze_timeframe, analyze_market, derive_bias, detect_live_signal

def make_series(start=3000, step=1, n=120):
    out = []
    p = start
    for i in range(n):
        o = p
        c = p + step
        hi = max(o, c) + 0.4
        lo = min(o, c) - 0.4
        out.append(Candle(str(i), o, hi, lo, c))
        p = c
    return out

bull = make_series(step=1)
a = analyze_timeframe("M5", bull)
assert a.trend == "ALCISTA"

market = {tf: bull for tf in ["M1","M5","M15","H1","H4"]}
analyses = analyze_market(market)
bias, score = derive_bias(analyses)
assert bias == "ALCISTA"
signal, _, _, reasons = detect_live_signal(analyses)
assert signal in ("BUY CANDIDATE", "WAIT")
print("V2 tests OK:", a, bias, score, signal)
