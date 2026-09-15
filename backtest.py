from __future__ import annotations
from dataclasses import dataclass
from typing import List
from market_data import Candle
from analytics import ema, atr

@dataclass
class BacktestResult:
    trades: int
    wins: int
    losses: int
    win_rate: float
    net_r: float
    expectancy_r: float
    max_losing_streak: int
    note: str

def quick_trend_backtest(candles: List[Candle], rr=3.0):
    """
    Simple research backtest:
    EMA20/50 trend + pullback close crossing EMA20.
    SL = 1.25 ATR, TP = rr * risk.
    Not the full live strategy; used only as a sanity-check baseline.
    """
    if len(candles) < 100:
        return BacktestResult(0,0,0,0,0,0,0,"Muestra insuficiente.")

    closes=[c.close for c in candles]
    e20=ema(closes,20)
    e50=ema(closes,50)
    wins=losses=0
    net_r=0.0
    losing_streak=max_losing_streak=0
    i=55

    while i < len(candles)-2:
        c=candles[i]
        prev=candles[i-1]
        direction=None
        if e20[i] > e50[i] and prev.close <= e20[i-1] and c.close > e20[i]:
            direction="BUY"
        elif e20[i] < e50[i] and prev.close >= e20[i-1] and c.close < e20[i]:
            direction="SELL"

        if not direction:
            i += 1
            continue

        a=atr(candles[:i+1],14)
        if a <= 0:
            i+=1; continue

        entry=c.close
        risk=a*1.25
        sl=entry-risk if direction=="BUY" else entry+risk
        tp=entry+risk*rr if direction=="BUY" else entry-risk*rr

        outcome=None
        j=i+1
        while j < min(len(candles), i+31):
            x=candles[j]
            if direction=="BUY":
                sl_hit=x.low <= sl
                tp_hit=x.high >= tp
            else:
                sl_hit=x.high >= sl
                tp_hit=x.low <= tp
            if sl_hit and tp_hit:
                outcome="LOSS"  # conservative: assume SL first
                break
            if sl_hit:
                outcome="LOSS"; break
            if tp_hit:
                outcome="WIN"; break
            j += 1

        if outcome=="WIN":
            wins += 1; net_r += rr; losing_streak=0
        elif outcome=="LOSS":
            losses += 1; net_r -= 1; losing_streak += 1
            max_losing_streak=max(max_losing_streak,losing_streak)

        i=max(i+1,j)

    trades=wins+losses
    wr=(wins/trades*100) if trades else 0
    exp=(net_r/trades) if trades else 0
    note="Baseline simple, NO es backtest completo de la estrategia sniper."
    return BacktestResult(trades,wins,losses,round(wr,1),round(net_r,2),round(exp,2),max_losing_streak,note)
