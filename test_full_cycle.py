"""
AI_OPTIX Full Cycle Test — Greek Spark
=======================================
Runs ONE complete trading cycle with:
  - Real Groq AI (uses your GROQ_API_KEY from .env)
  - Mock broker server (synthetic NSE market data)
  - Paper trading ON (no real orders)
  - Market hours overridden (runs any time of day)

Usage:
    # Terminal 1: start mock broker
    python mock_broker_server.py

    # Terminal 2: run this test
    uv run python test_full_cycle.py
"""

import asyncio
import subprocess
import sys
import time
import os

def wait_for_broker(timeout=8):
    import urllib.request
    for _ in range(timeout * 2):
        try:
            urllib.request.urlopen("http://127.0.0.1:5000/health", timeout=1)
            return True
        except Exception:
            time.sleep(0.5)
    return False

# ── Start mock broker if not already running ─────────────────────────────────
broker_proc = None
try:
    import urllib.request
    urllib.request.urlopen("http://127.0.0.1:5000/health", timeout=1)
    print("[TEST] Mock broker already running on :5000")
except Exception:
    print("[TEST] Starting mock broker...")
    broker_proc = subprocess.Popen(
        [sys.executable, "mock_broker_server.py"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    if not wait_for_broker():
        print("[TEST] ERROR: Mock broker failed to start. Check mock_broker_server.py")
        sys.exit(1)
    print("[TEST] Mock broker started OK")

# ── Import agent (picks up .env and connects to mock broker) ─────────────────
import agent as _ag

# Override market hours so cycle runs regardless of wall clock time
_ag.MARKET_OPEN_HOUR   = 0
_ag.MARKET_OPEN_MINUTE = 0
_ag.SQUARE_OFF_HOUR    = 23
_ag.SQUARE_OFF_MINUTE  = 59

# ── Run the full trading cycle ────────────────────────────────────────────────
async def main():
    print("\n" + "=" * 72)
    print("[TEST] AI_OPTIX Full Cycle Test — Greek Spark")
    print("[TEST] One complete cycle: fetch → analyze → risk check → order")
    print("=" * 72 + "\n")

    print("[TEST] Step 1: Initialize trading state (funds + positions from mock broker)...")
    await _ag.initialize_trading_state()

    print("\n[TEST] Step 2: Run full trading cycle (real Groq AI decisions)...")
    await _ag.run_trading_cycle()

    print("\n" + "=" * 72)
    print("[TEST] Cycle complete. Review output above.")
    print("[TEST] What to check:")
    print("  [OK] Init shows Rs.500,000 available cash")
    print("  [OK] Market data fetched for all 5 symbols")
    print("  [OK] Risk checks ran per symbol")
    print("  [OK] BUY/SELL/HOLD decision per symbol")
    print("  [OK] PAPER TRADING order IDs (PAPER#####, not real broker)")
    print("  [OK] Token usage + estimated cost shown at end")
    print("=" * 72 + "\n")

asyncio.run(main())

# ── Cleanup ───────────────────────────────────────────────────────────────────
if broker_proc:
    broker_proc.terminate()
    print("[TEST] Mock broker stopped.")
