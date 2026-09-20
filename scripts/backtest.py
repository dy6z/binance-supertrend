#!/usr/bin/env python3
import sys
import os
import argparse
from pathlib import Path
import pandas as pd
import numpy as np

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.binance_client import BinanceFuturesClient
from src.indicators import calculate_supertrend

def run_backtest(symbol="BTC/USDT:USDT", timeframe="5m", limit=1000, period=10, multiplier=3.0, fee_pct=0.0005):
    print(f"\n--- Backtesting Supertrend ({period}, {multiplier}) on {symbol} [{timeframe}] ---")
    client = BinanceFuturesClient(sandbox=False)
    df = client.fetch_ohlcv_df(symbol, timeframe=timeframe, limit=limit)
    
    df = calculate_supertrend(df, period=period, multiplier=multiplier)
    
    trades = []
    current_trade = None

    for i in range(period + 1, len(df)):
        signal = df["st_signal"].iloc[i]
        price = df["close"].iloc[i]
        time = df["datetime"].iloc[i]

        if signal in ["BUY", "SELL"]:
            # Close existing trade if flip
            if current_trade is not None:
                exit_price = price
                entry_price = current_trade["entry_price"]
                side = current_trade["side"]
                
                if side == "BUY":
                    pnl_pct = (exit_price - entry_price) / entry_price - (2 * fee_pct)
                else:
                    pnl_pct = (entry_price - exit_price) / entry_price - (2 * fee_pct)
                
                trades.append({
                    "entry_time": current_trade["entry_time"],
                    "exit_time": time,
                    "side": side,
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "pnl_pct": pnl_pct
                })
            
            # Open new trade
            current_trade = {
                "side": signal,
                "entry_price": price,
                "entry_time": time
            }

    if not trades:
        print("No trades generated.")
        return

    tdf = pd.DataFrame(trades)
    total_trades = len(tdf)
    winning_trades = len(tdf[tdf["pnl_pct"] > 0])
    win_rate = (winning_trades / total_trades) * 100
    cum_returns = (1 + tdf["pnl_pct"]).cumprod() - 1
    total_return = cum_returns.iloc[-1] * 100

    print(f"Total Trades: {total_trades}")
    print(f"Win Rate: {win_rate:.2f}% ({winning_trades}/{total_trades})")
    print(f"Total Cumulative Return: {total_return:.2f}% (incl. 0.05% taker fee/trade)")
    print("------------------------------------------------------------------------\n")

def main():
    parser = argparse.ArgumentParser(description="Backtest Supertrend Strategy")
    parser.add_argument("--symbol", default="BTC/USDT:USDT", help="Symbol to backtest")
    parser.add_argument("--timeframe", default="5m", help="Candle timeframe")
    parser.add_argument("--limit", type=int, default=1000, help="Candle count")
    args = parser.parse_args()

    run_backtest(symbol=args.symbol, timeframe=args.timeframe, limit=args.limit)

if __name__ == "__main__":
    main()
