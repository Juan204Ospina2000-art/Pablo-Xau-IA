from dataclasses import dataclass, asdict
from typing import Optional
from config import MIN_VALID_SCORE, WAIT_SCORE, DEFAULT_MIN_RR, RULE_WEIGHTS

@dataclass
class SetupInput:
    direction: str
    entry: float
    stop_loss: float
    take_profit: float
    trend_aligned: bool
    liquidity_sweep: bool
    structure_confirmation: bool
    valid_entry_zone: bool
    high_impact_news_near: bool
    price_extended: bool
    notes: str = ""

@dataclass
class SetupResult:
    direction: str
    entry: float
    stop_loss: float
    take_profit: float
    risk_points: float
    reward_points: float
    rr: float
    score: int
    decision: str
    quality: str
    reasons: list[str]
    warnings: list[str]

def calculate_rr(direction: str, entry: float, stop_loss: float, take_profit: float):
    direction = direction.upper()

    if direction == "BUY":
        risk = entry - stop_loss
        reward = take_profit - entry
    elif direction == "SELL":
        risk = stop_loss - entry
        reward = entry - take_profit
    else:
        raise ValueError("direction debe ser BUY o SELL")

    if risk <= 0:
        raise ValueError("El Stop Loss no es válido para esa dirección.")
    if reward <= 0:
        raise ValueError("El Take Profit no es válido para esa dirección.")

    return risk, reward, reward / risk

def evaluate_setup(data: SetupInput) -> SetupResult:
    risk, reward, rr = calculate_rr(
        data.direction, data.entry, data.stop_loss, data.take_profit
    )

    score = 0
    reasons = []
    warnings = []

    checks = [
        ("trend_aligned", data.trend_aligned, "Tendencia alineada"),
        ("liquidity_sweep", data.liquidity_sweep, "Sweep de liquidez"),
        ("structure_confirmation", data.structure_confirmation, "Confirmación estructural"),
        ("valid_entry_zone", data.valid_entry_zone, "Entrada en zona válida"),
    ]

    for key, active, label in checks:
        if active:
            score += RULE_WEIGHTS[key]
            reasons.append(f"+{RULE_WEIGHTS[key]} {label}")

    if rr >= DEFAULT_MIN_RR:
        score += RULE_WEIGHTS["rr_good"]
        reasons.append(f"+{RULE_WEIGHTS['rr_good']} R:R {rr:.2f} ≥ 1:{DEFAULT_MIN_RR:.0f}")
    else:
        warnings.append(f"R:R {rr:.2f} por debajo del objetivo 1:{DEFAULT_MIN_RR:.0f}")

    if data.high_impact_news_near:
        score += RULE_WEIGHTS["high_impact_news_near"]
        warnings.append("Noticia de alto impacto cercana")
        reasons.append(f"{RULE_WEIGHTS['high_impact_news_near']} Riesgo macro inmediato")

    if data.price_extended:
        score += RULE_WEIGHTS["price_extended"]
        warnings.append("Precio extendido: riesgo de perseguir entrada")
        reasons.append(f"{RULE_WEIGHTS['price_extended']} Precio extendido")

    # Filtros duros del modo sniper
    if data.high_impact_news_near and not data.structure_confirmation:
        decision = "NO TRADE"
        quality = "Bloqueado"
    elif data.price_extended and rr < DEFAULT_MIN_RR:
        decision = "NO TRADE"
        quality = "Bloqueado"
    elif score >= MIN_VALID_SCORE:
        decision = data.direction.upper()
        quality = "Setup válido"
    elif score >= WAIT_SCORE:
        decision = "WAIT"
        quality = "Casi válido"
    else:
        decision = "NO TRADE"
        quality = "Débil"

    return SetupResult(
        direction=data.direction.upper(),
        entry=data.entry,
        stop_loss=data.stop_loss,
        take_profit=data.take_profit,
        risk_points=round(risk, 3),
        reward_points=round(reward, 3),
        rr=round(rr, 2),
        score=score,
        decision=decision,
        quality=quality,
        reasons=reasons,
        warnings=warnings,
    )

def position_size(account_balance: float, risk_percent: float, risk_money_per_unit: float):
    """
    Calculadora genérica. Para lotaje real de XAUUSD hay que adaptar
    contract size/tick value al broker concreto.
    """
    if account_balance <= 0 or risk_percent <= 0 or risk_money_per_unit <= 0:
        raise ValueError("Los valores deben ser positivos.")
    max_loss = account_balance * (risk_percent / 100)
    units = max_loss / risk_money_per_unit
    return max_loss, units
