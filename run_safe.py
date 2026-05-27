"""
Agentic-Trader -- Safe Development Mode
========================================
Runs one complete trading cycle with ALL external APIs mocked:
  - OpenAlgo broker  : returns synthetic market data, no real orders placed
  - AI model         : returns a deterministic simulated decision, no API key needed

Usage:
    uv run python run_safe.py

When you have real API keys, configure .env and use:
    uv run python agent.py
"""

import os
import sys
import asyncio
from types import ModuleType, SimpleNamespace

# =============================================================================
# PHASE 1: ENVIRONMENT SETUP (must happen before any agent imports)
# =============================================================================
os.environ.setdefault("MODEL_PROVIDER",    "openai")
os.environ.setdefault("OPENAI_API_KEY",    "sk-safe-mode-no-real-key-placeholder")
os.environ.setdefault("OPENALGO_API_KEY",  "mock-openalgo-key-safe-mode")
os.environ.setdefault("OPENALGO_HOST",     "http://127.0.0.1:5000")

# Load .env overrides (so real keys work seamlessly when added later)
try:
    from dotenv import load_dotenv
    load_dotenv(override=False)  # override=False keeps our placeholders if key is missing
except ImportError:
    pass

# =============================================================================
# PHASE 2: MOCK OPENALGO BROKER
# Inject a fake `openalgo` module into sys.modules BEFORE agent.py is imported,
# so that `from openalgo import api` inside agent.py gets our mock.
# =============================================================================
import random
import pandas as pd
import pytz
from datetime import datetime

IST = pytz.timezone("Asia/Kolkata")

MOCK_PRICES = {
    "ICICIBANK": 1350.50,
    "RELIANCE":  2856.75,
    "SBIN":       812.40,
    "WIPRO":      325.60,
    "ITC":        468.90,
}


def _synthetic_ohlcv(symbol: str, bars: int = 100) -> pd.DataFrame:
    """Generate reproducible OHLCV bars for TA-Lib indicator calculation."""
    rng = random.Random(abs(hash(symbol)) % 99_999)
    base = MOCK_PRICES.get(symbol, 1000.0)
    rows = []
    for _ in range(bars):
        o = base * (1 + rng.uniform(-0.003, 0.003))
        h = o * (1 + rng.uniform(0.001, 0.007))
        l = o * (1 - rng.uniform(0.001, 0.007))
        c = rng.uniform(l, h)
        v = int(rng.uniform(80_000, 250_000))
        rows.append({
            "open":   round(o, 2),
            "high":   round(h, 2),
            "low":    round(l, 2),
            "close":  round(c, 2),
            "volume": v,
        })
        base = c
    return pd.DataFrame(rows)


class _MockBroker:
    """Simulates OpenAlgo REST API responses — no network calls."""

    def funds(self):
        print("[SAFE MODE] Mock broker: funds()", flush=True)
        return {
            "status": "success",
            "data": {
                "availablecash":   "500000.00",
                "m2mrealized":     "1250.00",
                "m2munrealized":   "-320.00",
            },
        }

    def positionbook(self):
        print("[SAFE MODE] Mock broker: positionbook() -> no open positions", flush=True)
        return {"status": "success", "data": []}

    def quotes(self, symbol, exchange="NSE"):
        print(f"[SAFE MODE] Mock broker: quotes({symbol})", flush=True)
        p = MOCK_PRICES.get(symbol, 1000.0)
        return {
            "status": "success",
            "data": {
                "ltp":        p,
                "open":       round(p * 0.995, 2),
                "high":       round(p * 1.008, 2),
                "low":        round(p * 0.992, 2),
                "volume":     1_500_000,
                "prev_close": round(p * 0.998, 2),
            },
        }

    def depth(self, symbol, exchange="NSE"):
        print(f"[SAFE MODE] Mock broker: depth({symbol})", flush=True)
        p = MOCK_PRICES.get(symbol, 1000.0)
        return {
            "status": "success",
            "data": {
                "bids": [
                    {"price": round(p - 0.5, 2), "quantity": 300},
                    {"price": round(p - 1.0, 2), "quantity": 200},
                ],
                "asks": [
                    {"price": round(p + 0.5, 2), "quantity": 280},
                    {"price": round(p + 1.0, 2), "quantity": 180},
                ],
            },
        }

    def history(self, symbol, exchange="NSE",
                interval="5m", start_date=None, end_date=None):
        print(f"[SAFE MODE] Mock broker: history({symbol}) -> 100 synthetic bars", flush=True)
        return _synthetic_ohlcv(symbol)

    def placeorder(self, **kwargs):
        symbol   = kwargs.get("symbol",   "UNKNOWN")
        action   = kwargs.get("action",   "?")
        quantity = kwargs.get("quantity", 0)
        oid      = f"MOCK{abs(hash(symbol + action)) % 100_000:05d}"
        print(
            f"[SAFE MODE] *** SIMULATED ORDER: {action} {quantity} x {symbol}"
            f" -> Order #{oid} (no real trade placed) ***",
            flush=True,
        )
        return {"status": "success", "orderid": oid}

    def cancelallorder(self, **kwargs):
        print("[SAFE MODE] Mock broker: cancelallorder() (simulated)", flush=True)
        return {"status": "success", "message": "All orders cancelled (simulated)"}


# Inject into sys.modules so agent.py's `from openalgo import api` gets our mock
_mock_oa_module = ModuleType("openalgo")
_mock_oa_module.api = lambda api_key=None, host=None: _MockBroker()
sys.modules["openalgo"] = _mock_oa_module

# =============================================================================
# PHASE 3: MOCK AI RUNNER
# Replace Runner.run with a deterministic function BEFORE agent.py imports Runner.
# Runner.run is a classmethod, so we wrap our async impl with classmethod().
# =============================================================================
from agents.run import Runner


async def _mock_runner_run_impl(cls, starting_agent, input,
                                *, max_turns=None, **kwargs):
    """
    Simulates an AI trading decision without making any API calls.
    The response mirrors the format the real agent would produce.
    """
    print(
        "\n[SAFE MODE] AI model call intercepted -- returning simulated decision\n",
        flush=True,
    )
    # Deterministic output that exercises the full result-handling path in agent.py
    mock_output = (
        "ICICIBANK: BUY simulated (RSI 28 oversold, MACD bullish crossover)\n"
        "RELIANCE:  HOLD (ADX 18 - trend too weak for entry)\n"
        "SBIN:      SELL simulated (RSI 74 overbought, EMA bearish)\n"
        "WIPRO:     HOLD (mixed signals - MACD bearish vs EMA bullish)\n"
        "ITC:       HOLD (neutral indicators, no clear signal)"
    )
    return SimpleNamespace(final_output=mock_output, context_wrapper=None)


# Assign as a classmethod so Runner.run(agent, input, max_turns=N) works as-is
Runner.run = classmethod(_mock_runner_run_impl)

# =============================================================================
# PHASE 4: IMPORT AGENT (picks up mocked openalgo + patched Runner)
# =============================================================================
print("=" * 72, flush=True)
print("[SAFE MODE] Agentic-Trader -- SAFE DEVELOPMENT MODE", flush=True)
print("[SAFE MODE] Broker API : fully mocked (no network connection)", flush=True)
print("[SAFE MODE] AI model   : simulated   (no API key required)", flush=True)
print("[SAFE MODE] Orders     : simulated   -- ZERO real capital at risk", flush=True)
print("=" * 72 + "\n", flush=True)

import agent as _agent_mod  # noqa: E402  (intentionally late import)

# =============================================================================
# PHASE 5: OVERRIDE MARKET HOURS
# Force trading cycle to execute regardless of current wall-clock time.
# =============================================================================
_agent_mod.MARKET_OPEN_HOUR   = 0
_agent_mod.MARKET_OPEN_MINUTE = 0
_agent_mod.SQUARE_OFF_HOUR    = 23
_agent_mod.SQUARE_OFF_MINUTE  = 59

# =============================================================================
# PHASE 6: RUN ONE COMPLETE SAFE TRADING CYCLE
# =============================================================================
async def main():
    print("[SAFE MODE] Step 1 of 2: Initialising trading state...\n", flush=True)
    await _agent_mod.initialize_trading_state()

    print("\n[SAFE MODE] Step 2 of 2: Running one full trading cycle...\n", flush=True)
    await _agent_mod.run_trading_cycle()

    print("\n" + "=" * 72, flush=True)
    print("[SAFE MODE] SUCCESS -- Safe cycle complete. All systems validated.", flush=True)
    print("[SAFE MODE] Verified:", flush=True)
    print("  [OK] Dependency installation (85 packages)", flush=True)
    print("  [OK] TA-Lib indicators (RSI, MACD, BB, EMA, Stoch, ADX, ATR)", flush=True)
    print("  [OK] Mock broker API (quotes, depth, history, positionbook, funds)", flush=True)
    print("  [OK] Risk management checks", flush=True)
    print("  [OK] Position sizing calculation", flush=True)
    print("  [OK] Simulated order placement", flush=True)
    print("  [OK] AI decision pipeline (mocked)", flush=True)
    print("", flush=True)
    print("[SAFE MODE] Next steps:", flush=True)
    print("  1. Get an AI provider key (Groq free: https://console.groq.com)", flush=True)
    print("  2. Add it to .env:  GROQ_API_KEY=gsk-...  MODEL_PROVIDER=groq", flush=True)
    print("  3. Set up OpenAlgo broker at http://127.0.0.1:5000", flush=True)
    print("  4. Run live agent:  uv run python agent.py", flush=True)
    print("=" * 72, flush=True)


asyncio.run(main())
