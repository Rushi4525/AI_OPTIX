"""
AI_OPTIX Data Fetcher  —  Greek Spark
Real historical NSE data via Yahoo Finance + TA-Lib indicators.

Features:
  • Fetches 5-day 5-minute OHLCV for all 5 NSE symbols
  • 5-minute thread-safe in-memory cache (avoids hammering Yahoo)
  • Computes RSI, MACD, Bollinger Bands, EMA-20/50, Stochastic, ADX, ATR
  • Returns last 30 closes as sparkline data
  • Falls back gracefully if Yahoo Finance is unavailable
"""

import threading
import time
import warnings
from datetime import datetime, date

import numpy as np
import pytz
import talib

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

IST = pytz.timezone("Asia/Kolkata")

# NSE symbol → Yahoo Finance ticker
_NS = {
    "ICICIBANK": "ICICIBANK.NS",
    "RELIANCE":  "RELIANCE.NS",
    "SBIN":      "SBIN.NS",
    "WIPRO":     "WIPRO.NS",
    "ITC":       "ITC.NS",
}

_CACHE:      dict          = {}   # symbol → (fetched_at, df)
_CACHE_TTL:  int           = 300  # 5 minutes
_LOCK:       threading.Lock = threading.Lock()
_FETCHING:   set           = set()  # symbols currently being fetched (dedup)


# ── Data fetch ────────────────────────────────────────────────────────────────

def _yf_fetch(symbol: str):
    """
    Fetch 5-day 5-minute OHLCV from Yahoo Finance.
    Returns a pandas DataFrame or None on failure.
    """
    try:
        import yfinance as yf
        ns  = _NS.get(symbol, symbol + ".NS")
        df  = yf.Ticker(ns).history(period="5d", interval="5m", auto_adjust=True)
        if df is None or df.empty:
            return None
        df.columns = [c.lower() for c in df.columns]
        df = df[["open", "high", "low", "close", "volume"]].dropna()
        return df
    except Exception:
        return None


def get_history(symbol: str):
    """
    Return cached OHLCV DataFrame for symbol, refreshing every 5 minutes.
    Returns None if data is unavailable.
    """
    now = time.time()
    with _LOCK:
        if symbol in _CACHE:
            ts, df = _CACHE[symbol]
            if now - ts < _CACHE_TTL:
                return df
        if symbol in _FETCHING:
            # Another thread is fetching — return stale data if available
            return _CACHE.get(symbol, (None, None))[1]
        _FETCHING.add(symbol)

    try:
        df = _yf_fetch(symbol)
        with _LOCK:
            if df is not None:
                _CACHE[symbol] = (now, df)
            _FETCHING.discard(symbol)
        return df
    except Exception:
        with _LOCK:
            _FETCHING.discard(symbol)
        return None


def warm_cache(symbols: list) -> None:
    """Pre-warm the cache for all symbols in parallel threads."""
    threads = [threading.Thread(target=get_history, args=(s,)) for s in symbols]
    for t in threads:
        t.start()
    for t in threads:
        t.join()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _last(arr) -> float:
    """Last non-NaN value from a numpy array."""
    valid = arr[~np.isnan(arr)]
    return round(float(valid[-1]), 2) if len(valid) else 0.0


def _prev_close(df) -> float:
    """
    Approximate previous trading day's closing price.
    Uses the last close of the day BEFORE the most recent trading day.
    """
    try:
        if hasattr(df.index, "tz_convert"):
            idx = df.index.tz_convert(IST)
        else:
            idx = df.index
        today_d = idx[-1].date()
        prev_bars = df[idx.map(lambda x: x.date()) < today_d]
        if not prev_bars.empty:
            return round(float(prev_bars["close"].iloc[-1]), 2)
        # Fallback: first bar of full dataset
        return round(float(df["close"].iloc[0]), 2)
    except Exception:
        return round(float(df["close"].iloc[0]), 2) if not df.empty else 0.0


# ── Public API ─────────────────────────────────────────────────────────────────

_NEUTRAL = {
    "rsi": 50.0, "rsiSignal": "neutral",
    "macdTrend": "neutral", "emaTrend": "neutral",
    "adx": 0.0, "trendStrength": "weak",
    "sparkData": [],
}


def compute_indicators(symbol: str) -> dict:
    """
    Compute all 7 TA-Lib indicators on real yfinance data.
    Returns a dict ready to merge into the dashboard state.
    Falls back to neutral values if data unavailable (< 55 bars).
    """
    df = get_history(symbol)
    if df is None or len(df) < 55:
        return dict(_NEUTRAL)

    close  = df["close"].values.astype(float)
    high   = df["high"].values.astype(float)
    low    = df["low"].values.astype(float)

    # 1. RSI
    rsi_a = talib.RSI(close, 14)
    rsi   = _last(rsi_a)

    # 2. MACD
    macd_a, sig_a, _ = talib.MACD(close, 12, 26, 9)
    macd  = _last(macd_a)
    sig   = _last(sig_a)

    # 3. EMA 20/50
    ema20 = _last(talib.EMA(close, 20))
    ema50 = _last(talib.EMA(close, 50))

    # 4. Bollinger Bands
    ub, mb, lb = talib.BBANDS(close, 20)
    ltp = round(float(close[-1]), 2)
    bb_pos = "overbought" if ltp > _last(ub) else "oversold" if ltp < _last(lb) else "neutral"

    # 5. ADX (trend strength)
    adx_a = talib.ADX(high, low, close, 14)
    adx   = _last(adx_a)

    # 6. ATR (volatility)
    atr_a = talib.ATR(high, low, close, 14)
    atr   = _last(atr_a)

    # 7. Stochastic
    sk, sd = talib.STOCH(high, low, close)
    stoch  = _last(sk)

    # Sparkline — last 30 valid close prices (≈ 2.5 hours of 5-min bars)
    valid_close = close[~np.isnan(close)]
    spark = [round(float(x), 2) for x in valid_close[-30:]]

    return {
        "rsi":          rsi,
        "rsiSignal":    "overbought" if rsi > 70 else "oversold" if rsi < 30 else "neutral",
        "macdTrend":    "bullish"    if macd > sig  else "bearish",
        "emaTrend":     "bullish"    if ema20 > ema50 else "bearish",
        "bbPosition":   bb_pos,
        "adx":          adx,
        "trendStrength":"strong" if adx > 25 else "weak",
        "atr":          atr,
        "stoch":        stoch,
        "sparkData":    spark,
    }


def get_quote(symbol: str) -> dict:
    """
    Return current price info from the most recent yfinance bar.
    Dict keys match the dashboard state schema.
    """
    df = get_history(symbol)
    if df is None or df.empty:
        return {"ltp": 0.0, "prevClose": 0.0, "changePct": 0.0, "volume": 0}

    ltp       = round(float(df["close"].iloc[-1]), 2)
    prev      = _prev_close(df)
    chg       = round((ltp - prev) / prev * 100, 2) if prev else 0.0
    vol       = int(df["volume"].sum())

    return {
        "ltp":       ltp,
        "prevClose": prev,
        "changePct": chg,
        "volume":    vol,
    }
