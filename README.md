# Binance Futures SuperTrend Bot (Production)

Standalone automated trading bot for Binance USD-M Futures based on the SuperTrend indicator with Flip Logic. 

## Strategy: SuperRWI Flip
- **SuperTrend**: Standard Wilder's RMA SuperTrend.
- **RWI (Range Weighted Index)**: Used as a volatility-based trend strength filter (customizable per symbol).
- **Pivot Filter**: Automatically excludes entries near 20-bar Pivot Highs/Lows to avoid buying tops/selling bottoms.
- **Flip Execution**: Automatically flips positions (closes SHORT before opening LONG, and vice versa) upon signal direction changes. No static TP/SL — trends are held until reversal.

## Production Directory Structure
```text
binance-supertrend/
├── config/
│   └── settings.yaml      # Symbol-specific configurations (RWI Triggers, Pairs)
├── data/                  # Historical CSV data for backtesting
├── logs/                  # Execution and error logs
├── src/
│   ├── engine.py          # Trade logic (Flip + Pivot Filter)
│   ├── indicators.py      # Technical indicators (SuperTrend, RWI, Pivot)
│   ├── runner.py          # Main daemon runner loop
│   └── binance_client.py  # Binance API integration
└── scripts/               # Production utility scripts
```

## Setup & Maintenance
1. **Config**: Edit `config/settings.yaml` to adjust trading pairs, leverage, or RWI triggers per symbol.
2. **Monitoring**: View logs in `logs/runner.log`.
3. **Backtesting**: Use `scripts/backtest.py` with deterministic CSV data to validate strategies before any config change.
