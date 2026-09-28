# Binance Futures SuperRWI Bot

Automated trading bot for Binance USD-M Futures using SuperTrend + Range Weighted Index (RWI) + Pivot Filter. Optimized for 6 specific crypto symbols on 15m timeframe.

## Strategy: SuperRWI + Hybrid Exit
- **Execution Model**: **Closed-Candle Evaluation**. The bot ignores forming candles (`df.iloc[:-1]`) to ensure parity with TradingView alerts and backtest results.
- **SuperTrend**: Base trend detection (Period 10, Multiplier 3.0).
- **RWI (Range Weighted Index)**: Volatility filter. Buy/Sell triggers are blocked unless RWI > trigger threshold.
- **Pivot S&R Filter**: Blocks Buying at Resistance or Selling at Support using a 20-bar lookback.
- **Hybrid Exit**: Combines SuperTrend reversal (Flip) with fixed TP/SL and a Profit Lock safety mechanism.

## Backtest Results (60d Frozen Data)
Deterministic, reproducible via `python3 backtest_5sym.py` (1x, no-fee, 5,713–5,741 candles).

| Symbol | TP (%) | SL (%) | Lock (%) | RWI | PF | WR (%) | Trades | Ret 1x | MaxDD | Source File |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **1000PEPE** | 2.0 | 2.0 | 0.5 | 1.2 | **1.863** | 50.0 | 44 | 28.3% | 10.4% | `frozen_60d/1000PEPE.csv` |
| **BTC** | 2.0 | 2.0 | 0.5 | 1.2 | **1.571** | 45.5 | 33 | 6.3% | 3.9% | `frozen_60d/BTC.csv` |
| **ZEC** | 3.0 | 2.0 | 0.5 | 1.0 | **1.483** | 47.3 | 74 | 38.2% | 26.6% | `frozen_60d/ZEC.csv` |
| **SOL** | 1.5 | 2.5 | 1.0 | 1.0 | **1.136** | 41.2 | 68 | 5.2% | 13.2% | `~/.home/dy6z/sol_data_frozen.csv` |
| **SNDK** | 1.0 | 2.0 | 0.5 | 1.0 | **1.132** | 53.2 | 94 | 7.6% | 12.1% | `frozen_60d/SNDK.csv` |
| **INJ** | 1.5 | 2.0 | 0.0 | 1.0 | **1.174** | 52.2 | 90 | 12.0% | 17.6% | `frozen_60d/INJ.csv` |

**Total trades: 403**. Metrics are 1x no-fee for cross-symbol comparability.
Note: an older SOL snapshot (PF 2.01, WR 77.14%) was validated on a different dataset; current canonical run uses `sol_data_frozen.csv`.
INJ (added 2026-09-28) was the only survivor of a 7-candidate RWI-1.0 default screen; its `profit_lock` is intentionally 0.0 (unlike the others' 0.5/1.0) per the frozen grid result.

## Data Management (Frozen Snapshots)
To ensure deterministic results, all backtests and grid searches MUST use the following frozen snapshots:
- **BTC/SOL/ZEC/SNDK/PEPE/INJ**: Snapshots stored in `frozen_60d/` and `data_snapshot/`.
- **Validation**: Every strategy change must be verified against `backtest_5sym.py` to ensure no regression in combined Profit Factor.

## Maintenance Log
- **2026-09-28 (night)**: Fixed critical `cleanup_algo_orders` bug — it passed the CCXT symbol format (`ZEC/USDT:USDT`) to the native algo API which expects the market id (`ZECUSDT`), so the filter was silently ignored and the call deleted the WHOLE account's open TP/SL algos (observed: ZEC's stop deleted under a "for SOL" log, INJ's stop under "for BTC"). Result: exchange-side stops disappeared, positions ran past their configured SL (ZEC closed −3.34% vs 2% configured). Fix: convert via `market_id()`, delete only orders whose `symbol` matches, with a per-order guard. Service restarted + TP/SL re-placed on all open positions; functional test confirms cross-symbol algos survive a cleanup of another symbol.
- **2026-09-28**: INJ added to live roster (TP1.5/SL2.0/lock0/RWI1.0). Also fixed a silent bug: `runner.py` had the symbol list HARDCODED, so edits to `strategy.symbols` in `settings.yaml` were ignored. The runner now reads the list from the YAML (single source of truth) — after any config change, verify the startup log line `Starting Binance SuperTrend Bot | Symbols: [...]` before trusting the roster.

## Directory Structure
```text
binance-supertrend/
├── config/
│   └── settings.yaml      # All tuning (TP/SL, RWI, Symbols)
├── frozen_60d/            # Frozen CSVs for deterministic backtesting
├── logs/                  # Execution logs
├── src/
│   ├── engine.py          # Core Logic (evaluates closed candles)
│   ├── runner.py          # Multi-symbol execution loop
│   ├── indicators.py      # Pine-Script-aligned technicals
│   └── binance_client.py  # REST API Client (F-API)
└── trade_log.csv          # Real-world trade history
```

## Quick Start

### 1. Run Strategy Backtest (Frozen Data)
```bash
python3 backtest_5sym.py
```

### 2. Start Bot Runner (Production)
```bash
# Must be run from project root with PYTHONPATH
PYTHONPATH=. python3 -m src.runner
```

### 3. Check Service Status
```bash
systemctl --user status binance-supertrend.service
journalctl --user -u binance-supertrend.service -f
```

## Systemd Setup (Auto-Start & Crash Recovery)

The bot runs as a systemd **user service** with `Restart=always`, so it survives reboots and auto-recovers from crashes.

### 1. Create the Unit File
Write to `~/.config/systemd/user/binance-supertrend.service`:

```ini
[Unit]
Description=Binance Futures SuperTrend Bot
After=network.target

[Service]
WorkingDirectory=/home/dy6z/workspace/binance-supertrend
ExecStart=/usr/bin/python3 -m src.runner
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
```

Notes:
- `python3 -m src.runner` (not `python3 src/runner.py`) is required: bare script execution drops the project root from `sys.path` and fails with `ModuleNotFoundError: No module named 'src'`.
- `WorkingDirectory` sets the project root so `config/settings.yaml` and relative paths resolve.

### 2. Reload & Enable
```bash
systemctl --user daemon-reload
systemctl --user enable --now binance-supertrend.service
```

### 3. Operate
```bash
systemctl --user status binance-supertrend.service   # check
systemctl --user restart binance-supertrend.service # restart after code changes
journalctl --user -u binance-supertrend.service -f   # live logs
```

> Login manager note: user services only run while the user session is active.
> On a headless VPS, enable lingering so the service starts at boot:
> `sudo loginctl enable-linger $USER`

## Maintenance Rules
1. **Never evaluate forming candles**: The bot MUST use `df.iloc[:-1]` to maintain parity with backtests.
2. **Deterministic Validation**: Before changing any param in `settings.yaml`, run the full 5-symbol backtest on frozen data to ensure PF improvement.
3. **Orphaned Algo Orders**: If a position closes via the exchange-side TP/SL trigger, the sibling algo order is left open. The engine now self-heals this on the next cycle when it detects a flat position, but for manual cleanups use the `fapiPrivateGetOpenAlgoOrders` API.
4. **Security**: Ensure `.env` is in `.gitignore` (contains API credentials).
5. **Visual Validation**: Use `make_super_rwi_visual.py` to verify trade labels against TradingView.
