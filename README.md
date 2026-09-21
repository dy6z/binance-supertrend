# Binance Futures SuperTrend Bot (Production)

Standalone automated trading bot for Binance USD-M Futures based on the SuperTrend indicator with Flip Logic.

## Strategy: SuperRWI + Pivot Filter
- **SuperTrend**: Standard Wilder's RMA SuperTrend.
- **RWI (Range Weighted Index)**: Volatility-based trend strength filter (customizable per symbol).
  - **Tuning**: ETH (1.0), SOL/ZEC/SNDK (1.3 optimized).
- **Pivot Filter (S&R)**: Dynamically calculates Pivot Highs/Lows (20-bar rolling window).
  - **Resistance Filter**: Blocks BUY signals if `close > (PivotHigh * 0.999)`.
  - **Support Filter**: Blocks SELL signals if `close < (PivotLow * 1.001)`.
- **Flip Execution**: Automatically flips positions (closes SHORT before opening LONG, and vice versa) upon signal direction changes. No static TP/SL — trends are held until reversal.

## Performance Metrics (Deterministic)
- **Dataset**: 10,000 candles per symbol (15m timeframe).
- **Duration**: ~104 days (~3.5 months) of continuous data.

| Symbol | Trades | WR (%) | PF | Return |
| :--- | :---: | :---: | :---: | :--- |
| **ETH** | 116 | 34.5% | 1.08 | 85.01 |
| **SOL** | 76 | 36.8% | 1.51 | 16.51 |
| **ZEC** | 72 | 45.8% | 2.35 | 561.22 |
| **SNDK** | 89 | 40.4% | 1.31 | 283.55 |

**Total Trades: 353**

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

## Service Management
The bot runs as a systemd user service.

- **Check status:**
  ```bash
  systemctl --user status binance-supertrend.service
  ```
- **Stop bot:**
  ```bash
  systemctl --user stop binance-supertrend.service
  ```
- **Start bot:**
  ```bash
  systemctl --user start binance-supertrend.service
  ```
- **View logs:**
  ```bash
  tail -f logs/runner.log
  ```

## Setup & Maintenance
1. **Config**: Edit `config/settings.yaml` to adjust trading pairs, leverage, or RWI triggers per symbol.
2. **Backtesting**: Use `scripts/backtest.py` with deterministic CSV data to validate strategies before any config change.
3. **Security**: Ensure `.env` is in `.gitignore` (contains API credentials).
