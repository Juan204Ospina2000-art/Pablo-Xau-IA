APP_NAME = "Pablo XAU AI"
SYMBOL = "XAUUSD"

MIN_VALID_SCORE = 6
WAIT_SCORE = 4
DEFAULT_MIN_RR = 3.0

RULE_WEIGHTS = {
    "trend_aligned": 1,
    "liquidity_sweep": 2,
    "structure_confirmation": 2,
    "valid_entry_zone": 1,
    "rr_good": 2,
    "high_impact_news_near": -2,
    "price_extended": -2,
}

DISCLAIMER = (
    "Score interno de calidad del setup; no representa una probabilidad "
    "estadística garantizada de beneficio."
)
