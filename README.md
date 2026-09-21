# Binance Futures SuperTrend Bot (Production)

Standalone automated trading bot for Binance USD-M Futures based on the SuperTrend indicator with Flip Logic.

## Strategy: SuperRWI + Pivot Filter
- **SuperTrend**: Standard Wilder's RMA SuperTrend.
- **RWI (Range Weighted Index)**: Volatility-based trend strength filter (customizable per symbol).
- **Pivot Filter (S&R)**: Dynamically calculates Pivot Highs/Lows (20-bar rolling window).
  - **Resistance Filter**: Blocks BUY signals if `close > (PivotHigh * 0.999)`.
  - **Support Filter**: Blocks SELL signals if `close < (PivotLow * 1.001)`.
- **Flip Execution**: Automatically flips positions (closes SHORT before opening LONG, and vice versa) upon signal direction changes. No static TP/SL — trends are held until reversal.

## Directory Structure
```text
binance-supertrend/
├── config/
│   └── settings.yaml      # Symbol-specific configurations (RWI Triggers, Pairs)
├── data/                  # Historical CSV data
├── logs/                  # Execution and error logs
├── src/
│   ├── engine.py          # Logic: SuperTrend + RWI + Pivot Filter + Flip
│   ├── indicators.py      # Technical indicators (SuperTrend, RWI, Pivot)
│   ├── runner.py          # Main daemon runner loop
│   └── binance_client.py  # Binance API integration
└── scripts/               # Utility scripts & Backtesters
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

## Setup & Maintenance
1. **Config**: Edit `config/settings.yaml` to adjust trading pairs, leverage, or RWI triggers per symbol.
2. **Monitoring**: View logs in `logs/runner.log`.
3. **Backtesting**: Use `scripts/backtest.py` to validate logic changes.
