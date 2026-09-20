# Binance Futures SuperTrend Bot

Standalone automated trading bot for Binance USD-M Futures based on the SuperTrend indicator with Flip Logic. Runs entirely in Python without requiring a TradingView subscription.

## Architecture & Features
- **Data Source:** Binance Futures REST API via CCXT (OHLCV).
- **Strategy:** Exact Wilder's RMA SuperTrend calculation matching TradingView (`period=10, multiplier=3.0`).
- **Flip Execution:** Automatically flips positions (closes SHORT before opening LONG, and vice versa) upon signal direction changes.
- **Risk Management:** Configurable margin per trade (e.g. $1 USDT), leverage (10x), and optional bracket Take Profit & Stop Loss.
- **Backtesting Module:** Includes offline backtester across historical Binance Futures candles.

## Directory Structure
```
binance-supertrend/
├── config/
│   └── settings.yaml      # Pairs, timeframe, risk, leverage, and TP/SL settings
├── data/                  # Local cache
├── logs/                  # Execution and error logs
├── scripts/
│   ├── backtest.py        # Strategy backtester
│   └── status.py          # Account balance & open positions inspector
├── src/
│   ├── binance_client.py  # CCXT Binance Futures client
│   ├── engine.py          # Trade logic and flip execution engine
│   ├── indicators.py      # Vectorized Wilder's SuperTrend indicator
│   └── runner.py          # Main daemon runner loop
├── requirements.txt
└── README.md
```

## Quick Start

### 1. Test Strategy Backtest
```bash
python3 scripts/backtest.py --symbol BTC/USDT:USDT --timeframe 5m --limit 1000
```

### 2. Check Account Status & Open Positions
```bash
python3 scripts/status.py
```

### 3. Run Single Evaluation Cycle (Dry-run / Test)
```bash
python3 src/runner.py --once
```

### 4. Run Continuous Daemon
```bash
python3 src/runner.py
```
