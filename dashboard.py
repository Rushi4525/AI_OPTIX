"""
AI_OPTIX Dashboard  —  Greek Spark
Real-time trading dashboard: FastAPI + WebSockets + Alpine.js
"""

import asyncio
import concurrent.futures
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pytz
import talib
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

# ── Silence noise before agent import ───────────────────────────────────────
os.environ.setdefault("OPENAI_API_KEY", "no-tracing-disabled")
import litellm as _ll; _ll.suppress_debug_info = True; _ll.set_verbose = False  # noqa: E702

import agent as _ag  # shared: trade_state, client, SYMBOLS, PAPER_TRADING, model_name …

IST       = pytz.timezone("Asia/Kolkata")
TEMPLATES = Path(__file__).parent / "templates"
_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=20)
_T0       = time.time()

# ── Agent task state ─────────────────────────────────────────────────────────
_agent_task: asyncio.Task | None = None
_agent_running  = False
_last_cycle_ts  = 0.0
_CYCLE_SECS     = 300

from contextlib import asynccontextmanager

@asynccontextmanager
async def _lifespan(application):
    import urllib.request
    try:
        urllib.request.urlopen("http://127.0.0.1:5000/health", timeout=1)
        print("[DASHBOARD] Mock broker on :5000  ✓")
    except Exception:
        print("[DASHBOARD] Starting mock broker …")
        subprocess.Popen([sys.executable, "mock_broker_server.py"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        await asyncio.sleep(1.5)
    print("[DASHBOARD]  Open →  http://127.0.0.1:8080")
    yield

app = FastAPI(title="AI_OPTIX", docs_url=None, redoc_url=None, lifespan=_lifespan)


# ── Pure sync helpers (run in thread executor) ────────────────────────────────

def _fetch_quote(symbol: str) -> dict:
    try:
        r = _ag.client.quotes(symbol=symbol, exchange="NSE")
        if r.get("status") == "success":
            d    = r["data"]
            ltp  = float(d.get("ltp", 0))
            prev = float(d.get("prev_close", ltp) or ltp)
            chg  = round((ltp - prev) / prev * 100, 2) if prev else 0.0
            return {"ltp": round(ltp, 2), "prevClose": round(prev, 2),
                    "changePct": chg, "volume": int(d.get("volume", 0))}
    except Exception:
        pass
    return {"ltp": 0.0, "prevClose": 0.0, "changePct": 0.0, "volume": 0}


def _fetch_indicators(symbol: str) -> dict:
    _NEUTRAL = {"rsi": 50.0, "rsiSignal": "neutral",
                "macdTrend": "neutral", "emaTrend": "neutral", "sparkData": []}
    try:
        end   = datetime.now(IST).strftime("%Y-%m-%d")
        start = (datetime.now(IST) - timedelta(days=3)).strftime("%Y-%m-%d")
        r = _ag.client.history(symbol=symbol, exchange="NSE",
                               interval="5m", start_date=start, end_date=end)
        if isinstance(r, dict):
            return _NEUTRAL

        close = r["close"].values
        high  = r["high"].values
        low   = r["low"].values

        def _last(a):
            v = a[~np.isnan(a)]
            return round(float(v[-1]), 2) if len(v) else 0.0

        rsi_a            = talib.RSI(close, 14)
        macd_a, sig_a, _ = talib.MACD(close, 12, 26, 9)
        ema20_a          = talib.EMA(close, 20)
        ema50_a          = talib.EMA(close, 50)

        rsi  = _last(rsi_a)
        macd = _last(macd_a)
        sig  = _last(sig_a)
        e20  = _last(ema20_a)
        e50  = _last(ema50_a)

        return {
            "rsi":       rsi,
            "rsiSignal": "overbought" if rsi > 70 else "oversold" if rsi < 30 else "neutral",
            "macdTrend": "bullish" if macd > sig  else "bearish",
            "emaTrend":  "bullish" if e20  > e50  else "bearish",
            "sparkData": [round(float(x), 2) for x in close[-20:]],
        }
    except Exception:
        return _NEUTRAL


def _fetch_positions() -> list:
    try:
        r = _ag.client.positionbook()
        if r.get("status") == "success":
            out = []
            for p in r.get("data", []):
                qty = int(float(p.get("quantity", 0)))
                if qty != 0:
                    out.append({
                        "symbol":    p.get("symbol", ""),
                        "quantity":  qty,
                        "avgPrice":  round(float(p.get("average_price", 0)), 2),
                        "ltp":       round(float(p.get("ltp", 0)), 2),
                        "pnl":       round(float(p.get("pnl", 0)), 2),
                        "direction": "LONG" if qty > 0 else "SHORT",
                    })
            return out
    except Exception:
        pass
    return []


def _fetch_cash() -> float:
    try:
        r = _ag.client.funds()
        if r.get("status") == "success":
            return float(r["data"].get("availablecash", 0))
    except Exception:
        pass
    return 0.0


def _broker_ok() -> bool:
    try:
        return _ag.client.funds().get("status") == "success"
    except Exception:
        return False


# ── Async state builder (fans out to thread pool) ────────────────────────────

async def _build_state() -> dict:
    loop = asyncio.get_event_loop()
    run  = lambda fn, *a: loop.run_in_executor(_EXECUTOR, fn, *a)  # noqa: E731

    q_futs = {s: run(_fetch_quote,      s) for s in _ag.SYMBOLS}
    i_futs = {s: run(_fetch_indicators, s) for s in _ag.SYMBOLS}
    p_fut  = run(_fetch_positions)
    c_fut  = run(_fetch_cash)
    b_fut  = run(_broker_ok)

    quotes   = {s: await f for s, f in q_futs.items()}
    indics   = {s: await f for s, f in i_futs.items()}
    pos      = await p_fut
    cash     = await c_fut
    broker   = await b_fut

    # last decision per symbol from trade history
    decisions = {s: "HOLD" for s in _ag.SYMBOLS}
    for t in reversed(_ag.trade_state["trade_history"]):
        sym, act = t.get("symbol"), t.get("action")
        if sym and act in ("BUY", "SELL") and decisions.get(sym) == "HOLD":
            decisions[sym] = act

    tc        = _ag.trade_state["trade_counts"]
    daily_pnl = _ag.trade_state["daily_pnl"]
    next_cyc  = max(0, round(_CYCLE_SECS - (time.time() - _last_cycle_ts))) \
                if _last_cycle_ts else 0

    symbols_out = {}
    for s in _ag.SYMBOLS:
        symbols_out[s] = {**quotes[s], **indics[s],
                          "lastDecision": decisions[s],
                          "tradesToday":  tc.get(s, 0)}

    return {
        "paper_trading":  _ag.PAPER_TRADING,
        "agent_running":  _agent_running,
        "market_open":    _market_open(),
        "kpi": {
            "dailyPnl":      round(daily_pnl, 2),
            "availableCash": round(cash, 2),
            "openPositions": len(pos),
            "totalTrades":   sum(tc.values()),
        },
        "symbols":    symbols_out,
        "positions":  pos,
        "agentStatus": {
            "modelProvider":    _ag.MODEL_PROVIDER,
            "modelName":        _ag.model_name,
            "nextCycleSeconds": next_cyc,
            "nextCycleTotal":   _CYCLE_SECS,
            "stopLossHit":      _ag.trade_state["stop_loss_hit"],
            "stopLossPct":      round(
                min(100, abs(min(0.0, daily_pnl)) / abs(_ag.DAILY_STOP_LOSS) * 100), 1),
            "stopLossLimit":    abs(_ag.DAILY_STOP_LOSS),
            "squaredOffToday":  _ag.trade_state.get("squared_off_today", False),
            "tradeLimits": [
                {"symbol": s, "used": tc.get(s, 0), "max": _ag.MAX_TRADES_PER_SYMBOL}
                for s in _ag.SYMBOLS
            ],
        },
        "trade_history": _ag.trade_state["trade_history"][-50:],
        "systemStats": {
            "uptimeSeconds":   round(time.time() - _T0),
            "brokerConnected": broker,
        },
    }


def _market_open() -> bool:
    n = datetime.now(IST)
    return (n.weekday() < 5
            and (n.hour > 9 or (n.hour == 9 and n.minute >= 15))
            and (n.hour < 15 or (n.hour == 15 and n.minute < 15)))


# ── Agent loop ────────────────────────────────────────────────────────────────

async def _agent_loop():
    global _last_cycle_ts
    await _ag.initialize_trading_state()
    while _agent_running:
        _last_cycle_ts = time.time()
        await _ag.run_trading_cycle()
        await asyncio.sleep(_CYCLE_SECS)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def root():
    return HTMLResponse((TEMPLATES / "dashboard.html").read_text(encoding="utf-8"))


@app.get("/api/state")
async def api_state():
    return await _build_state()


@app.post("/api/agent/start")
async def api_start():
    global _agent_task, _agent_running
    if _agent_running:
        return {"status": "already_running"}
    _agent_running = True
    _agent_task = asyncio.create_task(_agent_loop())
    return {"status": "started"}


@app.post("/api/agent/stop")
async def api_stop():
    global _agent_running
    _agent_running = False
    if _agent_task and not _agent_task.done():
        _agent_task.cancel()
    return {"status": "stopped"}


@app.websocket("/ws")
async def ws_handler(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            payload = await _build_state()
            await ws.send_text(json.dumps(payload, default=str))
            await asyncio.sleep(3)
    except (WebSocketDisconnect, Exception):
        pass


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 56)
    print("  AI_OPTIX Dashboard  ·  Greek Spark")
    print("  Open  →  http://127.0.0.1:8080")
    print("=" * 56)
    uvicorn.run("dashboard:app", host="0.0.0.0", port=8080,
                reload=False, log_level="warning")
