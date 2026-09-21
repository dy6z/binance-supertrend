#!/usr/bin/env python3.12
"""
Fetch daily candles for FX pairs via yfinance (same as ML4T Forex).
Saves to ../data/candles.pkl
"""
import pickle
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

# Import from config
import sys
sys.path.insert(0, str(Path(__file__).parent))
from config import PAIRS, SYMBOL_MAP


def fetch_candles(period="5y", save=True):
    """
    Fetch daily candles for all pairs.
    
    Args:
        period: yfinance period (5y, 2y, etc.)
        save: save to pickle
        
    Returns:
        dict: {pair_name: list of dicts with OHLC + timestamp_ms}
    """
    candles = {}
    
    print(f"Fetching {len(PAIRS)} pairs from yfinance ({period} daily)...")
    
    for pair in PAIRS:
        # yfinance format: AUDJPY=X
        ticker = SYMBOL_MAP[pair] + "=X"
        
        try:
            data = yf.download(ticker, period=period, interval="1d", progress=False)
            
            if data.empty:
                print(f"  {pair}: no data")
                continue
            
            # Convert to list of dicts
            bars = []
            for idx, row in data.iterrows():
                bars.append({
                    "open": float(row["Open"].iloc[0] if hasattr(row["Open"], "iloc") else row["Open"]),
                    "high": float(row["High"].iloc[0] if hasattr(row["High"], "iloc") else row["High"]),
                    "low": float(row["Low"].iloc[0] if hasattr(row["Low"], "iloc") else row["Low"]),
                    "close": float(row["Close"].iloc[0] if hasattr(row["Close"], "iloc") else row["Close"]),
                    "volume": int(row["Volume"].iloc[0] if hasattr(row["Volume"], "iloc") else row["Volume"]) if "Volume" in row else 0,
                    "timestamp_ms": int(idx.timestamp() * 1000),
                    "spread_pips": 0.0,
                })
            
            candles[pair] = bars
            print(f"  {pair}: {len(bars)} bars")
            
        except Exception as e:
            print(f"  {pair}: ERROR {e}")
    
    if save and candles:
        out_path = Path(__file__).parent.parent / "data" / "candles.pkl"
        out_path.parent.mkdir(exist_ok=True)
        with open(out_path, "wb") as f:
            pickle.dump(candles, f)
        print(f"\nSaved: {out_path}")
    
    return candles


if __name__ == "__main__":
    fetch_candles()
