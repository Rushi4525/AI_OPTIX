"""
AI_OPTIX Mock Broker Server by Greek Spark
============================================
A zero-dependency local HTTP server that perfectly mimics the OpenAlgo REST API.
Generates realistic synthetic NSE market data so agent.py runs without any real broker.

Usage (Terminal 1):
    python mock_broker_server.py

Usage (Terminal 2):
    uv run python agent.py

.env settings required:
    OPENALGO_API_KEY=mock-key-aioptix-greekspark
    OPENALGO_HOST=http://127.0.0.1:5000
    PAPER_TRADING=true
"""

import json
import math
import random
import time
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = 5000
MOCK_API_KEY = "mock-key-aioptix-greekspark"

# Realistic base prices for NSE stocks
BASE_PRICES = {
    "ICICIBANK": 1347.50,
    "RELIANCE":  2863.40,
    "SBIN":       812.80,
    "WIPRO":      327.20,
    "ITC":        469.55,
}

# ---------------------------------------------------------------------------
# Synthetic OHLCV generator — produces stable, TA-Lib-compatible price series
# ---------------------------------------------------------------------------

def _make_ohlcv_bars(symbol: str, n_bars: int = 120) -> list:
    """
    Generate n_bars of 5-minute OHLCV data ending right now.
    Uses a seeded random walk so results are consistent per symbol per session.
    Produces enough bars for all 7 TA-Lib indicators (RSI/MACD/BB/EMA/Stoch/ADX/ATR).
    """
    rng = random.Random(abs(hash(symbol)) % 99_999)
    base = BASE_PRICES.get(symbol, 1000.0)

    # Add a slow intraday drift to make indicators more interesting
    drift = rng.choice([-0.0002, 0.0001, 0.0002, 0.0003])

    bars = []
    now_ts = int(time.time())
    bar_seconds = 5 * 60  # 5-minute bars

    price = base
    for i in range(n_bars):
        ts = now_ts - (n_bars - i) * bar_seconds

        price = price * (1 + drift + rng.uniform(-0.0025, 0.0025))
        spread = price * rng.uniform(0.001, 0.006)

        o = round(price * (1 + rng.uniform(-0.001, 0.001)), 2)
        h = round(o + abs(rng.gauss(0, spread * 0.5)), 2)
        l = round(o - abs(rng.gauss(0, spread * 0.5)), 2)
        c = round(rng.uniform(l, h), 2)
        v = int(rng.uniform(50_000, 400_000))

        bars.append({
            "timestamp": ts,
            "open":      o,
            "high":      h,
            "low":       l,
            "close":     c,
            "volume":    v,
        })
        price = c

    return bars


# Cache bars per symbol for the session (consistent across multiple calls)
_bar_cache: dict = {}

def get_bars(symbol: str) -> list:
    if symbol not in _bar_cache:
        _bar_cache[symbol] = _make_ohlcv_bars(symbol)
    return _bar_cache[symbol]


# ---------------------------------------------------------------------------
# Request handler
# ---------------------------------------------------------------------------

class OpenAlgoMockHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[MOCK] {ts}  {fmt % args}")

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        try:
            return json.loads(raw)
        except Exception:
            return {}

    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        # Strip prefix  /api/v1/
        path = self.path.rstrip("/")
        endpoint = path.split("/")[-1]

        body = self._read_body()
        symbol = body.get("symbol", "ICICIBANK")
        price = BASE_PRICES.get(symbol, 1000.0)

        # ----------------------------------------------------------------
        # Route to handler
        # ----------------------------------------------------------------

        if endpoint == "funds":
            self._send_json({
                "status": "success",
                "data": {
                    "availablecash":   "500000.00",
                    "collateral":      "0.00",
                    "m2mrealized":     "1250.00",
                    "m2munrealized":   "-320.00",
                    "utiliseddebits":  "0.00",
                }
            })

        elif endpoint == "positionbook":
            # Return empty positions — agent starts fresh each day
            self._send_json({"status": "success", "data": []})

        elif endpoint == "orderbook":
            self._send_json({"status": "success", "data": {"orders": [], "statistics": {
                "total_buy_orders": 0, "total_sell_orders": 0,
                "total_completed_orders": 0, "total_open_orders": 0,
                "total_rejected_orders": 0
            }}})

        elif endpoint == "quotes":
            rng = random.Random(int(time.time() / 5) + abs(hash(symbol)))
            ltp = round(price * (1 + rng.uniform(-0.003, 0.003)), 2)
            self._send_json({
                "status": "success",
                "data": {
                    "ltp":        ltp,
                    "open":       round(price * 0.995, 2),
                    "high":       round(price * 1.010, 2),
                    "low":        round(price * 0.990, 2),
                    "volume":     random.randint(800_000, 4_000_000),
                    "prev_close": round(price * 0.998, 2),
                }
            })

        elif endpoint == "depth":
            rng = random.Random(int(time.time() / 5) + abs(hash(symbol)) + 1)
            ltp = round(price * (1 + rng.uniform(-0.002, 0.002)), 2)
            self._send_json({
                "status": "success",
                "data": {
                    "bids": [
                        {"price": round(ltp - 0.50, 2), "quantity": rng.randint(200, 600)},
                        {"price": round(ltp - 1.00, 2), "quantity": rng.randint(100, 400)},
                        {"price": round(ltp - 1.50, 2), "quantity": rng.randint(50,  300)},
                        {"price": round(ltp - 2.00, 2), "quantity": rng.randint(30,  200)},
                        {"price": round(ltp - 2.50, 2), "quantity": rng.randint(20,  150)},
                    ],
                    "asks": [
                        {"price": round(ltp + 0.50, 2), "quantity": rng.randint(180, 550)},
                        {"price": round(ltp + 1.00, 2), "quantity": rng.randint(90,  380)},
                        {"price": round(ltp + 1.50, 2), "quantity": rng.randint(40,  280)},
                        {"price": round(ltp + 2.00, 2), "quantity": rng.randint(25,  180)},
                        {"price": round(ltp + 2.50, 2), "quantity": rng.randint(15,  130)},
                    ],
                }
            })

        elif endpoint == "history":
            bars = get_bars(symbol)
            self._send_json({"status": "success", "data": bars})

        elif endpoint == "placeorder":
            sym    = body.get("symbol", "UNKNOWN")
            action = body.get("action", "BUY")
            qty    = body.get("quantity", "1")
            oid    = f"MOCK{abs(hash(sym + action + str(time.time()))) % 100_000:05d}"
            print(f"[MOCK ORDER] {action} {qty} x {sym} → #{oid}")
            self._send_json({"status": "success", "orderid": oid})

        elif endpoint == "cancelallorder":
            self._send_json({"status": "success", "message": "All orders cancelled (mock)"})

        elif endpoint == "closeposition":
            self._send_json({"status": "success", "message": "Positions closed (mock)"})

        else:
            # Generic OK for any unhandled endpoint
            self._send_json({"status": "success", "data": {}})

    # Silence the default GET 404 noise
    def do_GET(self):
        if self.path == "/health":
            self._send_json({"status": "ok", "server": "AI_OPTIX Mock Broker by Greek Spark"})
        else:
            self._send_json({"status": "error", "message": "Use POST /api/v1/<endpoint>"}, 404)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", PORT), OpenAlgoMockHandler)
    print("=" * 60)
    print("  AI_OPTIX Mock Broker Server  —  Greek Spark")
    print(f"  Listening on  http://127.0.0.1:{PORT}")
    print("  Endpoints: quotes, depth, history, funds,")
    print("             positionbook, placeorder, cancelallorder")
    print()
    print("  .env keys needed:")
    print(f"    OPENALGO_API_KEY={MOCK_API_KEY}")
    print(f"    OPENALGO_HOST=http://127.0.0.1:{PORT}")
    print("    PAPER_TRADING=true")
    print()
    print("  Press Ctrl+C to stop.")
    print("=" * 60)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[MOCK] Server stopped.")
        server.server_close()
