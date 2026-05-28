# AI_OPTIX - Architecture by Greek Spark

**Version**: 3.1 (Production-Ready with Startup Initialization)
**Last Updated**: January 2025
**Status**: Production Ready ✅

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Design](#architecture-design)
3. [Key Features](#key-features)
4. [Technical Stack](#technical-stack)
5. [Startup Initialization](#startup-initialization)
6. [Trading Tools](#trading-tools)
7. [Data Flow](#data-flow)
8. [Risk Management](#risk-management)
9. [Market Hours Protection](#market-hours-protection)
10. [Performance Optimization](#performance-optimization)
11. [LiteLLM Integration](#litellm-integration)
12. [Configuration](#configuration)
13. [Deployment](#deployment)

---

## System Overview

The **Autonomous Trading Agent** is a highly optimized, single-agent AI trading system that makes fully autonomous trading decisions using technical analysis, parallel data processing, and instant market order execution. Built with the OpenAI Agents SDK and LiteLLM support, it provides ultra-fast, cost-effective algorithmic trading.

### Design Philosophy

**Version 3.0** represents a complete architecture overhaul focused on:

1. **Speed**: Parallel data fetching reduces cycle time from 12-20s to 2-3s
2. **Efficiency**: Token usage reduced by 79% (from 144K to 30K per cycle)
3. **Simplicity**: Single autonomous agent instead of 7+ specialized agents
4. **Cost**: 65% reduction in API costs through optimization
5. **Reliability**: Market orders execute instantly vs 15-45s for limit orders

---

## Architecture Design

### Single-Agent Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   🎯 AUTONOMOUS TRADING AGENT                    │
│                     (Single Unified Agent)                       │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
        ┌──────────────────────────────────────────────┐
        │          BULK OPERATIONS (PARALLEL)          │
        │                                              │
        │  📊 get_all_market_data()                   │
        │     • Fetches ALL 5 symbols in parallel     │
        │     • Returns quotes, depth, 7 TA-Lib      │
        │     • Threading + rate limiting             │
        │     • 2-3s execution time                   │
        └──────────────────────────────────────────────┘
                                │
                                ▼
        ┌──────────────────────────────────────────────┐
        │       INDIVIDUAL DECISION MAKING             │
        │                                              │
        │  For each symbol:                            │
        │  • 🛡️ check_risk_constraints()              │
        │  • 🧮 calculate_position_size()             │
        │  • 🧠 Analyze 7 TA-Lib indicators           │
        │  • Make BUY/SELL/HOLD decision              │
        └──────────────────────────────────────────────┘
                                │
                                ▼
        ┌──────────────────────────────────────────────┐
        │        BULK ORDER EXECUTION (PARALLEL)       │
        │                                              │
        │  ⚡ place_bulk_orders()                      │
        │     • Places ALL orders simultaneously      │
        │     • Market orders (instant execution)     │
        │     • Rate limiting: 0.5s per 2 orders      │
        │     • Returns all order IDs                 │
        └──────────────────────────────────────────────┘
                                │
                                ▼
        ┌──────────────────────────────────────────────┐
        │             🏦 OPENALGO BROKER API            │
        │  • Order placement • Position tracking       │
        │  • Market data     • Account management      │
        └──────────────────────────────────────────────┘
```

### Why Single-Agent?

**Previous multi-agent architecture issues:**
- High token usage (144K+ per cycle)
- Slow handoffs between 7 specialized agents
- Complex memory session management
- Higher API costs ($0.023-0.031 per cycle)
- Verbose logging and output

**Current single-agent benefits:**
- 79% lower token usage (~30K per cycle)
- No agent handoff overhead
- Simplified codebase (50% less code)
- 65% cost reduction ($0.008-0.012 per cycle)
- Faster cycles (2-3s data fetch, 3-6s total)

---

## Key Features

### ✅ Core Capabilities

- **5 Symbols**: ICICIBANK, RELIANCE, SBIN, WIPRO, ITC
- **7 TA-Lib Indicators**: RSI, MACD, Bollinger Bands, EMA, Stochastic, ADX, ATR
- **Parallel Data Fetching**: All symbols fetched simultaneously (2-3s)
- **Market Orders**: Instant execution (no waiting for fills)
- **Bulk Operations**: Single API call for multiple orders
- **Rate Limiting**: Respects broker's 10 req/sec limit
- **Shorting Enabled**: Can SELL without position (creates short)
- **Model Agnostic**: Supports Cerebras, Groq, OpenAI, custom models
- **Token Tracking**: Real-time cost monitoring
- **Strict Risk Controls**: Stop-loss, position limits, trade counts

### 🚀 Performance Metrics

| Metric | Previous | Current | Improvement |
|--------|----------|---------|-------------|
| Cycle Time | 12-20s | 3-6s | 70% faster |
| Data Fetch | 8-12s | 2-3s | 75% faster |
| Token Usage | 144K | 30K | 79% reduction |
| Cost/Cycle | $0.023-0.031 | $0.008-0.012 | 65% cheaper |
| Order Execution | 15-45s (limit) | Instant (market) | 100% faster |

---

## Technical Stack

### Core Technologies

- **Language**: Python 3.12+
- **AI Framework**: OpenAI Agents SDK
- **LLM Interface**: LiteLLM (model-agnostic)
- **Model Providers**: Cerebras, Groq, OpenAI
- **Technical Analysis**: TA-Lib (7 indicators)
- **Broker API**: OpenAlgo
- **Scheduler**: APScheduler (5-minute cycles)
- **Concurrency**: Threading (rate-limited)
- **Data Processing**: NumPy
- **Terminal UI**: Colorama
- **Configuration**: python-dotenv

### Dependencies

```toml
[project]
dependencies = [
    "openai-agents[litellm]>=1.0.0",
    "python-dotenv>=1.0.0",
    "apscheduler>=3.10.0",
    "colorama>=0.4.6",
    "ta-lib>=0.4.28",
    "numpy>=1.26.0",
    "openalgo>=1.0.0",
    "pytz>=2024.1"
]
```

---

## Startup Initialization

### Automatic State Detection

When the agent starts, it automatically initializes the trading state by fetching:

1. **Account Funds**
   - Available cash balance
   - M2M realized P&L
   - M2M unrealized P&L
   - Used margin/debits

2. **Open Positions**
   - All current positions with quantities
   - Average entry prices
   - Current LTP (Last Traded Price)
   - Profit/Loss per position
   - Position direction (long/short)

3. **Daily P&L Calculation**
   - Aggregates P&L from all positions
   - Updates `trade_state["daily_pnl"]`
   - Checks against stop-loss limit

4. **Stop-Loss Status**
   - Verifies if daily loss limit exceeded
   - Sets `stop_loss_hit` flag if needed
   - Blocks trading if stop-loss triggered

### Initialization Output Example

```
================================================================================
[INIT] Initializing Trading State...
================================================================================

[INIT] Fetching account funds...
[INIT] ✓ Available Cash: Rs.10,500.00
[INIT] ✓ M2M Realized: Rs.150.00
[INIT] ✓ M2M Unrealized: Rs.-45.00

[INIT] Fetching open positions...
[INIT] ✓ Open Positions: 2
[INIT] Current Positions:
  • RELIANCE: Qty=-1, Avg=1180.50, LTP=1185.00, P&L=Rs.-4.50
  • WIPRO: Qty=41, Avg=238.20, LTP=240.50, P&L=Rs.94.30

[INIT] Calculating daily P&L...
[INIT] ✓ Daily P&L: Rs.89.80

[INIT] ✓ Stop-loss check: OK (limit: Rs.-10,000)

================================================================================
[INIT] ✓ Initialization Complete
================================================================================
```

### Benefits

- ✅ **Restart-Safe**: Can restart agent anytime without losing state
- ✅ **Position Awareness**: Knows all open positions before trading
- ✅ **Fund Verification**: Ensures sufficient capital available
- ✅ **P&L Continuity**: Tracks P&L across restarts
- ✅ **Risk Validation**: Checks stop-loss before first trade

### Implementation

```python
async def initialize_trading_state():
    """Initialize trading state by fetching current funds, positions, and P&L."""
    # 1. Fetch account funds
    funds_response = client.funds()

    # 2. Fetch open positions
    positions_response = client.positionbook()

    # 3. Calculate current P&L
    current_pnl = update_daily_pnl()

    # 4. Check stop-loss status
    if current_pnl <= DAILY_STOP_LOSS:
        trade_state["stop_loss_hit"] = True
```

---

## Trading Tools

### 1. 📊 Bulk Market Data Fetcher

**Function**: `get_all_market_data()`

**Purpose**: Fetch ALL market data for ALL 5 symbols in parallel

**Implementation**:
```python
@function_tool
def get_all_market_data() -> Dict[str, Any]:
    """Fetch quotes, depth, and historical data for all symbols.

    Uses threading to fetch all 5 symbols in parallel while
    respecting broker's 10 req/sec rate limit.

    Returns:
        Dict with data for all symbols including:
        - LTP, volume, bid/ask
        - 7 TA-Lib indicators (RSI, MACD, BB, EMA, Stoch, ADX, ATR)
        - Bid/ask ratio
        - Historical data (3 days)
    """
```

**Performance**:
- Execution time: 2-3 seconds
- Rate limiting: 0.15s delay between API calls
- Staggered starts: 0.2s between symbols
- Effective rate: 6-7 req/sec (safe buffer)

**Returns**:
```json
{
  "status": "success",
  "symbols_processed": 5,
  "data": {
    "ICICIBANK": {
      "ltp": 1345.90,
      "volume": 3613289,
      "indicators": {
        "rsi": 45.2,
        "macd": 1.5,
        "macd_signal": 1.2,
        "bb_upper": 1360.0,
        "bb_middle": 1345.0,
        "bb_lower": 1330.0,
        "ema_20": 1342.5,
        "stoch": 55.0,
        "adx": 28.5,
        "atr": 12.5
      },
      "bid_ask_ratio": 1.23
    }
    // ... other symbols
  }
}
```

### 2. 🛡️ Risk Constraint Checker

**Function**: `check_risk_constraints(symbol, action)`

**Purpose**: Validate each trade against risk rules

**Risk Rules**:
1. **Stop-Loss**: Max -Rs.10,000 daily loss
2. **Trade Limits**: Max 5 trades per symbol per day
3. **Position Control**:
   - BUY blocked if already long
   - SELL blocked if already short
   - Shorting allowed (SELL without position)
   - Covering allowed (BUY to close short)

**Returns**:
```json
{
  "allowed": true,
  "reason": "All checks passed",
  "daily_pnl": -500.0,
  "trades_today": 2,
  "has_position": false
}
```

### 3. 🧮 Position Size Calculator

**Function**: `calculate_position_size(symbol, ltp)`

**Purpose**: Calculate correct quantity for Rs.10,000 investment

**Formula**:
```python
quantity = int(10000 / ltp)
actual_investment = quantity * ltp
```

**Returns**:
```json
{
  "symbol": "ICICIBANK",
  "ltp": 1345.90,
  "quantity": 7,
  "investment": 9421.30
}
```

### 4. ⚡ Bulk Order Executor

**Function**: `place_bulk_orders(orders)`

**Purpose**: Place multiple market orders simultaneously

**Features**:
- Parallel execution using threading
- Rate limiting: 0.5s delay per 2 orders
- Market orders (instant execution)
- Automatic reason tracking
- Detailed logging per order

**Input Format**:
```json
[
  {
    "symbol": "ICICIBANK",
    "action": "BUY",
    "quantity": 7,
    "reason": "MACD bullish"
  },
  {
    "symbol": "WIPRO",
    "action": "SELL",
    "quantity": 41,
    "reason": "take profit"
  }
]
```

**Returns**:
```json
{
  "success": true,
  "total_orders": 2,
  "results": {
    "0": {"order_id": "240311000123", "symbol": "ICICIBANK"},
    "1": {"order_id": "240311000124", "symbol": "WIPRO"}
  }
}
```

### 5. 📈 Account & Position Tools

**Functions**:
- `get_account_snapshot()` - Available funds, margins, P&L
- `get_current_positions()` - Open positions with unrealized P&L
- `square_off_all_positions()` - Close all positions (3:15 PM)
- `cancel_all_pending_orders()` - Cancel unfilled orders

---

## Data Flow

### Complete Trading Cycle (5 Minutes)

```
1. CYCLE START (Every 5 minutes, 9:15 AM - 3:30 PM)
   │
   ├─> 2. BULK DATA FETCH (Parallel - 2-3s)
   │    └─> get_all_market_data()
   │         • Fetches ALL 5 symbols simultaneously
   │         • Returns quotes, depth, 7 TA-Lib indicators
   │         • Threading with rate limiting
   │
   ├─> 3. DECISION MAKING (Sequential per symbol)
   │    │
   │    └─> For each symbol:
   │         ├─> Analyze 7 TA-Lib indicators
   │         ├─> Check for 3+ aligned signals
   │         ├─> Make BUY/SELL/HOLD decision
   │         │
   │         ├─> If BUY/SELL:
   │         │    ├─> check_risk_constraints(symbol, action)
   │         │    └─> calculate_position_size(symbol, ltp)
   │         │
   │         └─> Add to orders list if allowed
   │
   ├─> 4. BULK ORDER EXECUTION (Parallel - <1s)
   │    └─> place_bulk_orders(orders_list)
   │         • Places ALL orders simultaneously
   │         • Market orders (instant execution)
   │         • Rate limiting: 0.5s per 2 orders
   │
   └─> 5. CYCLE COMPLETION
        ├─> Update trade state
        ├─> Display token usage
        └─> Wait for next 5-minute cycle
```

### Technical Indicators Analysis

**7 TA-Lib Indicators Used**:

1. **RSI (Relative Strength Index)**
   - Range: 0-100
   - Oversold: RSI < 30 (BUY signal)
   - Overbought: RSI > 70 (SELL signal)

2. **MACD (Moving Average Convergence Divergence)**
   - MACD > Signal: Bullish (BUY)
   - MACD < Signal: Bearish (SELL)
   - Histogram crossover: Momentum shift

3. **Bollinger Bands**
   - Price near lower band: Oversold (BUY)
   - Price near upper band: Overbought (SELL)
   - Band squeeze: Breakout imminent

4. **EMA (Exponential Moving Average)**
   - 20 EMA & 50 EMA calculated
   - Price > EMA: Uptrend (BUY)
   - Price < EMA: Downtrend (SELL)

5. **Stochastic Oscillator**
   - Range: 0-100
   - < 20: Oversold (BUY)
   - > 80: Overbought (SELL)

6. **ADX (Average Directional Index)**
   - Measures trend strength
   - ADX < 20: Weak trend (HOLD)
   - ADX > 25: Strong trend (TRADE)

7. **ATR (Average True Range)**
   - Volatility measurement
   - Used for stop-loss placement
   - Higher ATR = more volatile

**Decision Criteria**:
- Need 3+ aligned indicators to trade
- Mixed signals = HOLD
- Weak trend (ADX < 20) = HOLD

---

## Risk Management

### Multi-Layer Risk System

#### Layer 1: Pre-Trade Validation
```python
# Stop-loss check
if trade_state["daily_pnl"] <= DAILY_STOP_LOSS:
    return {"allowed": False, "reason": "Daily stop-loss hit"}

# Trade count check
if trade_state["trade_counts"][symbol] >= MAX_TRADES_PER_SYMBOL:
    return {"allowed": False, "reason": "Max trades reached"}

# Position check (prevent pyramiding)
if action == "BUY" and has_long_position:
    return {"allowed": False, "reason": "Already long"}
if action == "SELL" and has_short_position:
    return {"allowed": False, "reason": "Already short"}
```

#### Layer 2: Position Sizing
- Fixed Rs.10,000 investment per trade
- Automatic quantity calculation
- Prevents over-leverage

#### Layer 3: Shorting Controls
```python
# ALLOWED:
- SELL without position (creates short) ✅
- BUY to close short position ✅

# BLOCKED:
- Adding to existing long position ❌
- Adding to existing short position ❌
```

#### Layer 4: Daily Limits
- **Stop-Loss**: -Rs.10,000 daily loss
- **Trade Limit**: 5 trades per symbol per day
- **Trading Hours**: 9:15 AM - 3:20 PM IST (configurable)
- **Square-Off**: All positions closed by 3:20 PM

#### Layer 5: Smart Square-Off
Instead of using broker's `closeposition()`, the agent:
- Fetches position book
- For each open position (qty ≠ 0):
  - Long position (qty > 0) → Places SELL for exact quantity
  - Short position (qty < 0) → Places BUY for absolute quantity
- Uses market orders for instant execution
- Tracks success/failure per position
- Provides detailed logging

**Benefits:**
- ✅ Precise quantity control
- ✅ Transparency (see each order)
- ✅ Error handling per position
- ✅ No black-box broker logic

### Risk Configuration

```python
# Trading parameters (agent.py:92-97)
SYMBOLS = ["ICICIBANK", "RELIANCE", "SBIN", "WIPRO", "ITC"]
MAX_INVESTMENT_PER_TRADE = 10000  # Rs.10,000 per trade
DAILY_STOP_LOSS = -10000          # Max -Rs.10,000 loss/day
MAX_TRADES_PER_SYMBOL = 5         # Max 5 trades per symbol/day
EXCHANGE = "NSE"
PRODUCT = "MIS"                   # Intraday trading
```

---

## Market Hours Protection

### Trading Hours Enforcement

The agent automatically enforces market hours to prevent trading outside allowed times:

**Trading Hours**: 9:15 AM - 3:20 PM IST (Monday-Friday)

### Time-Based Logic

```python
async def run_trading_cycle():
    now = datetime.now(IST)

    # Before market open (< 9:15 AM)
    if now.hour < 9 or (now.hour == 9 and now.minute < 15):
        print("[INFO] Market not open yet. Trading starts at 9:15 AM IST.")
        return

    # After square-off time (>= 3:20 PM)
    if now.hour > 15 or (now.hour == 15 and now.minute >= 20):
        if not trade_state.get("squared_off_today", False):
            # Square off ONCE
            _square_off_all_positions_direct()
            _cancel_all_pending_orders_direct()
            trade_state["squared_off_today"] = True
        else:
            print("[INFO] Market closed. Trading resumes at 9:15 AM IST tomorrow.")
        return

    # Normal trading (9:15 AM - 3:20 PM)
    # ... trading logic ...
```

### Behavior by Time

| Time | Agent Behavior | Output |
|------|---------------|--------|
| **Before 9:15 AM** | Skip cycle | "Market not open yet" |
| **9:15 AM - 3:20 PM** | Normal trading | Process all symbols |
| **3:20 PM (first time)** | Square off once | Close all positions |
| **3:20 PM+** | Skip cycles | "Market closed" |
| **3:45 PM** | Reset state | Prepare for next day |

### Square-Off Protection

**Prevents Multiple Square-Offs:**
- Uses `squared_off_today` flag
- Square-off runs ONCE at 3:20 PM
- Subsequent cycles skip with message
- Flag resets at 3:45 PM daily

**Output Examples:**

```bash
# 3:20 PM - First cycle
Market Closing Time - Squaring Off All Positions
[SQUARE OFF] Checking open positions to close...
[DONE] Square-off completed. No more trading today.

# 3:25 PM - Subsequent cycle
[INFO] Market closed. Trading resumes at 9:15 AM IST tomorrow.

# 3:30 PM - Another cycle
[INFO] Market closed. Trading resumes at 9:15 AM IST tomorrow.
```

### Startup Time Checks

When starting the agent:

```python
# During market hours (9:15 AM - 3:20 PM)
if 9 <= now.hour < 15 or (now.hour == 15 and now.minute < 20):
    print("Running initial test cycle...")
    await run_trading_cycle()

# Outside market hours
else:
    print("Outside market hours. Waiting for next scheduled run.")
```

**Benefits:**
- ✅ No wasted API calls outside hours
- ✅ Prevents errors from broker API
- ✅ Safe to restart anytime
- ✅ Automatic daily reset
- ✅ Square-off runs only once

### Error Prevention

**Without Protection:**
```
[ORDER FAILED] HTTP 400: MIS orders cannot be placed after square-off time (15:15 IST)
```

**With Protection:**
```
[INFO] Market closed. Trading resumes at 9:15 AM IST tomorrow.
```

---

## Performance Optimization

### Key Optimizations Implemented

#### 1. Parallel Data Fetching
**Before**: Sequential API calls (8-12s)
```python
for symbol in symbols:
    quotes = get_quotes(symbol)  # 1-2s each
    depth = get_depth(symbol)     # 1-2s each
    history = get_history(symbol)  # 2-3s each
# Total: 4-7s per symbol × 5 = 20-35s
```

**After**: Parallel threading (2-3s)
```python
threads = []
for symbol in symbols:
    thread = Thread(target=fetch_data, args=(symbol,))
    threads.append(thread)
# Total: 2-3s for all 5 symbols
```

#### 2. Market Orders vs Limit Orders
**Before**: Limit orders with retry logic (15-45s)
- Place limit order
- Check order status
- Modify price if not filled
- Retry 3× with 5s delays
- Cancel if still pending

**After**: Market orders (instant)
- Place market order
- Executes immediately at market price
- No status checks needed
- No retry logic required

#### 3. Token Usage Reduction
**Before**: 144K tokens per cycle
- Multi-agent architecture (7 agents)
- Memory session accumulation
- Verbose instructions (80+ lines)
- Long query messages (40 lines)

**After**: 30K tokens per cycle
- Single agent
- No memory session
- Concise instructions (30 lines)
- Short query (1 line)

#### 4. Rate Limiting Strategy
```python
# Broker limit: 10 req/sec
# Our implementation: 6-7 req/sec (safe buffer)

# Data fetching:
time.sleep(0.15)  # Between API calls
time.sleep(0.2 * index)  # Staggered starts

# Order placement:
if (i + 1) % 2 == 0:
    time.sleep(0.5)  # After every 2 orders
```

### Performance Comparison

| Operation | Before | After | Improvement |
|-----------|--------|-------|-------------|
| Data Fetch (5 symbols) | 8-12s | 2-3s | 75% faster |
| Order Execution | 15-45s | <1s | 95% faster |
| Total Cycle Time | 12-20s | 3-6s | 70% faster |
| Token Usage | 144K | 30K | 79% reduction |
| Cost per Cycle | $0.023 | $0.008 | 65% cheaper |
| Daily Cost (Cerebras) | $74/mo | $26/mo | 65% cheaper |

---

## LiteLLM Integration

### Why LiteLLM?

**Problem**: OpenAI Agents SDK only works with OpenAI models by default.

**Solution**: LiteLLM acts as a universal adapter, making ANY LLM work with OpenAI's API format.

### Benefits

1. ✅ **Model Flexibility** - Use 100+ LLM providers
2. ✅ **Cost Optimization** - Switch to cheaper models
3. ✅ **Speed Optimization** - Use faster models (Cerebras 1800+ tok/s)
4. ✅ **No Vendor Lock-in** - Not tied to OpenAI
5. ✅ **Fallback Support** - Switch providers if one fails
6. ✅ **Consistent API** - Same code works with all providers

### Architecture

```
┌─────────────────────┐
│  OpenAI Agents SDK  │  (Only understands OpenAI format)
└──────────┬──────────┘
           │
           ▼
    ┌──────────────┐
    │   LiteLLM    │  ◄── Universal Translator
    └──────┬───────┘
           │
           ├──────────► OpenAI (gpt-4o-mini)
           ├──────────► Cerebras (llama3.1-8b) ⚡
           ├──────────► Groq (llama-3.3-70b) 💰
           ├──────────► Anthropic (claude-3.5)
           ├──────────► Google (gemini-pro)
           └──────────► 100+ other providers!
```

### Supported Providers

**100+ LLM Providers** including:

| Category | Providers |
|----------|-----------|
| **Major Cloud** | OpenAI, Anthropic, Google, Cohere, Mistral |
| **Ultra-Fast** | Cerebras (1800+ tok/s), Groq (500-800 tok/s) |
| **Self-Hosted** | Ollama, LM Studio, vLLM, LocalAI |
| **Enterprise** | AWS Bedrock, Azure OpenAI, Google Vertex AI |
| **Aggregators** | Together AI (50+ models), Replicate (100+ models) |

### Implementation

```python
# agent.py configuration
MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "openai").lower()

if MODEL_PROVIDER == "cerebras":
    # FASTEST for real-time trading (1800+ tok/s, 50ms latency)
    trading_model = LitellmModel(
        model="cerebras/llama3.1-8b",
        api_key=os.getenv("CEREBRAS_API_KEY"),
        api_base="https://api.cerebras.ai/v1"
    )

elif MODEL_PROVIDER == "groq":
    # CHEAP & FAST for development ($0.59/1M tokens)
    trading_model = LitellmModel(
        model="groq/llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY")
    )

elif MODEL_PROVIDER == "openai":
    # DEFAULT - Best quality (but slower)
    trading_model = LitellmModel(
        model="gpt-4o-mini",
        api_key=os.getenv("OPENAI_API_KEY")
    )

# Use the same model interface for ALL providers
agent = Agent(
    name="Trading Agent",
    model=trading_model,  # Works with ANY provider!
    tools=[...]
)
```

### Performance Comparison

| Provider | Model | Speed | Latency | Cost/1M | Best For |
|----------|-------|-------|---------|---------|----------|
| **OpenAI** | gpt-4o-mini | 50-100 tok/s | 500ms | $0.15/$0.60 | Quality |
| **Cerebras** | llama3.1-8b | **1800+ tok/s** ⚡ | **50ms** | $0.60 | **Production** |
| **Groq** | llama-3.3-70b | 500-800 tok/s | 100ms | **$0.59** 💰 | **Development** |
| **Anthropic** | claude-3.5 | 80-120 tok/s | 400ms | $3/$15 | Deep analysis |

### Trading Impact

**Example: 5-symbol analysis with 30K tokens**

| Metric | OpenAI | Cerebras | Groq |
|--------|--------|----------|------|
| Response Time | 3-5s | **0.5-1s** ⚡ | 1-2s |
| Cost per Cycle | $0.008 | $0.018 | **$0.018** 💰 |
| Daily Cost (75 cycles) | $0.60 | $1.35 | $1.35 |
| **Best For** | Cost | **Speed** | Balance |

### Switching Providers

**One environment variable change:**
```bash
# .env file
MODEL_PROVIDER=cerebras  # Ultra-fast production
MODEL_PROVIDER=groq      # Fast development
MODEL_PROVIDER=openai    # High quality
```

**Benefits:**
- No code changes required
- Instant switching between providers
- Test multiple models easily
- Fallback strategies possible

---

## Configuration

### Environment Variables (.env)

```bash
# Model Provider (cerebras, groq, openai, custom)
MODEL_PROVIDER=openai

# Cerebras (FASTEST - recommended for production)
CEREBRAS_API_KEY=csk-your-key-here
CEREBRAS_MODEL=cerebras/llama3.1-8b

# Groq (FAST & CHEAP - recommended for development)
GROQ_API_KEY=gsk-your-key-here
GROQ_MODEL=groq/llama-3.3-70b-versatile

# OpenAI (DEFAULT - best quality)
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o-mini

# OpenAlgo Broker
OPENALGO_API_KEY=your-openalgo-key
OPENALGO_HOST=http://127.0.0.1:5000
```

### Model Provider Comparison

| Provider | Model | Speed | Cost/1M tokens | Best For |
|----------|-------|-------|----------------|----------|
| Cerebras | llama3.1-8b | ⚡⚡⚡ Ultra-fast | $0.60 | Production trading |
| Groq | llama-3.3-70b | ⚡⚡ Fast | $0.59 | Development/testing |
| OpenAI | gpt-4o-mini | ⚡ Standard | $0.15/$0.60 | Quality reasoning |

### Scheduler Configuration

```python
# Trading cycles: Every 5 minutes during market hours
scheduler.add_job(
    run_trading_cycle,
    'cron',
    day_of_week='mon-fri',
    hour='9-15',          # 9 AM to 3 PM
    minute='*/5',         # Every 5 minutes
    id='trading_cycle'
)

# Daily state reset: 3:45 PM
scheduler.add_job(
    reset_daily_state,
    'cron',
    day_of_week='mon-fri',
    hour=15,
    minute=45,
    id='daily_reset'
)
```

---

## Deployment

### Prerequisites

1. **Python**: 3.12 or higher
2. **uv**: Fast Python package manager
3. **TA-Lib**: Binary installation required
4. **API Keys**:
   - Model provider (Cerebras/Groq/OpenAI)
   - OpenAlgo broker account

### Installation

```bash
# Clone repository
git clone https://github.com/GreekSpark/AI_OPTIX.git
cd AI_OPTIX

# Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Install TA-Lib (platform-specific)
# Windows: Download from https://ta-lib.org
# Linux: sudo apt-get install ta-lib
# Mac: brew install ta-lib
```

### Running the Agent

```bash
# Development mode (with test cycle)
uv run python agent.py

# Production mode (scheduled only)
# Edit agent.py and comment out line with:
# await run_trading_cycle()

# Then run:
uv run python agent.py
```

### Monitoring

The agent provides color-coded output:

```
================================================================================
Trading Cycle: 2025-01-15 10:30:00 IST
================================================================================

[BULK DATA] Fetching data for 5 symbols in parallel...
[BULK DATA] Completed in 2.3 seconds

ICICIBANK: BUY Order#123 (MACD bullish)
RELIANCE: HOLD (weak signals)
SBIN: HOLD (existing position)
WIPRO: SELL Order#124 (take profit)
ITC: HOLD (mixed signals)

================================================================================
[TOKEN USAGE] API Call Statistics:
  Requests:      3
  Input Tokens:  28,234
  Output Tokens: 2,851
  Total Tokens:  31,085
  Est. Cost:     $0.008
================================================================================
```

---

## File Structure

```
AI_OPTIX/
├── agent.py                 # Main trading agent
├── .env                     # Environment configuration (gitignored)
├── .env.example            # Example configuration
├── pyproject.toml          # Python dependencies
├── uv.lock                 # Dependency lock file
├── .gitignore              # Git ignore rules
├── README.md               # Quick start guide
├── ARCHITECTURE.md         # This file
├── MODEL_CONFIG.md         # Model provider details
├── TROUBLESHOOTING.md      # Common issues & fixes
└── trading_memory.db       # Trade history (gitignored)
```

---

## Troubleshooting

### Common Issues

**1. Import Error: Module not found**
```bash
uv sync
uv pip install --upgrade openai-agents
```

**2. TA-Lib Import Error**
```bash
# Install TA-Lib binary first, then:
uv pip install TA-Lib
```

**3. Rate Limit Exceeded**
```python
# Adjust delays in get_all_market_data():
time.sleep(0.2)  # Increase from 0.15
```

**4. Max Turns Exceeded**
```python
# Increase in agent.py:
result = Runner.run_streamed(
    max_turns=60  # Increase from 30
)
```

See [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for detailed solutions.

---

## License & Disclaimer

**⚠️ TRADING RISK DISCLAIMER**: This is an autonomous AI trading system. Trading involves substantial risk of loss. Use at your own risk. Always test in paper trading mode first. Past performance does not guarantee future results.

---

## Support & Resources

- **Documentation**: See docs/ folder
- **OpenAI Agents SDK**: https://openai.github.io/openai-agents-python/
- **LiteLLM**: https://docs.litellm.ai/
- **TA-Lib**: https://ta-lib.org/
- **OpenAlgo**: https://openalgo.in/

---

**Version**: 3.1 (Production-Ready with Full Protection)
**Architecture**: Single Autonomous Agent with Bulk Operations
**Trading Style**: Technical Analysis + Instant Market Orders
**Performance**: 70% faster, 79% less tokens, 65% cheaper
**New Features**: Startup initialization, market hours protection, smart square-off, P&L tracking
