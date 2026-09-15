import json
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Dict, List

BASE_URL = "https://api.twelvedata.com"
SYMBOL = "XAU/USD"

TIMEFRAMES = {
    "M1": "1min",
    "M5": "5min",
    "M15": "15min",
    "H1": "1h",
    "H4": "4h",
}

@dataclass
class Candle:
    datetime: str
    open: float
    high: float
    low: float
    close: float

class MarketDataError(RuntimeError):
    pass

def _request(endpoint: str, params: dict, api_key: str) -> dict:
    params = {**params, "apikey": api_key}
    url = f"{BASE_URL}/{endpoint}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Pablo-XAU-AI/2.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            payload = json.loads(r.read().decode("utf-8"))
    except Exception as exc:
        raise MarketDataError(f"No se pudo conectar con el proveedor: {exc}") from exc

    if isinstance(payload, dict) and payload.get("status") == "error":
        raise MarketDataError(payload.get("message", "Error del proveedor de datos"))
    return payload

def get_candles(api_key: str, interval: str, outputsize: int = 120) -> List[Candle]:
    if not api_key:
        raise MarketDataError("Falta la API key de Twelve Data.")

    payload = _request(
        "time_series",
        {
            "symbol": SYMBOL,
            "interval": interval,
            "outputsize": outputsize,
            "format": "JSON",
        },
        api_key,
    )

    values = payload.get("values") or []
    if not values:
        raise MarketDataError("El proveedor no devolvió velas para XAU/USD.")

    candles = []
    for x in reversed(values):  # oldest -> newest
        candles.append(
            Candle(
                datetime=x["datetime"],
                open=float(x["open"]),
                high=float(x["high"]),
                low=float(x["low"]),
                close=float(x["close"]),
            )
        )
    return candles

def get_all_timeframes(api_key: str, outputsize: int = 120) -> Dict[str, List[Candle]]:
    result = {}
    for label, interval in TIMEFRAMES.items():
        result[label] = get_candles(api_key, interval, outputsize)
    return result

def get_latest_price(candles_by_tf: Dict[str, List[Candle]]) -> float:
    # M1 is the closest approximation to current price in this V2.
    candles = candles_by_tf.get("M1") or next(iter(candles_by_tf.values()))
    return candles[-1].close
