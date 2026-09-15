from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

@dataclass
class TradePlan:
    direction: str
    entry_low: float
    entry_high: float
    stop_loss: float
    tp1: float
    tp2: float
    tp3: float
    rr1: float
    rr2: float
    rr3: float
    risk_distance: float
    lots_estimate: Optional[float]
    risk_amount: Optional[float]
    note: str

def build_trade_plan(direction, current_price, m5_basic, m5_adv,
                     balance=None, risk_pct=0.5, contract_size=100.0):
    atr = max(m5_adv.atr, 0.01)
    zone_half = atr * 0.12
    entry_low = current_price - zone_half
    entry_high = current_price + zone_half
    entry_mid = (entry_low + entry_high) / 2

    if direction == "BUY":
        technical_anchor = min(m5_basic.recent_low, m5_adv.range_low)
        stop = technical_anchor - atr * 0.20
        risk = entry_mid - stop
        if risk <= 0:
            stop = entry_mid - atr * 1.25
            risk = entry_mid - stop
        tp1 = entry_mid + risk * 2
        tp2 = entry_mid + risk * 3
        tp3 = entry_mid + risk * 5
    else:
        technical_anchor = max(m5_basic.recent_high, m5_adv.range_high)
        stop = technical_anchor + atr * 0.20
        risk = stop - entry_mid
        if risk <= 0:
            stop = entry_mid + atr * 1.25
            risk = stop - entry_mid
        tp1 = entry_mid - risk * 2
        tp2 = entry_mid - risk * 3
        tp3 = entry_mid - risk * 5

    lots = None
    risk_amount = None
    note = "Lotaje estimado usando contract size configurable; comprueba especificaciones de tu broker."
    if balance and balance > 0 and risk_pct > 0 and contract_size > 0 and risk > 0:
        risk_amount = balance * (risk_pct / 100)
        risk_per_lot = risk * contract_size
        lots = risk_amount / risk_per_lot

    return TradePlan(
        direction=direction,
        entry_low=round(entry_low, 3),
        entry_high=round(entry_high, 3),
        stop_loss=round(stop, 3),
        tp1=round(tp1, 3),
        tp2=round(tp2, 3),
        tp3=round(tp3, 3),
        rr1=2.0, rr2=3.0, rr3=5.0,
        risk_distance=round(risk, 3),
        lots_estimate=round(lots, 3) if lots else None,
        risk_amount=round(risk_amount, 2) if risk_amount else None,
        note=note,
    )
