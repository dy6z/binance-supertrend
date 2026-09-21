#!/usr/bin/env python3.12
"""
Generate trading signals using RSI + EMA + Stochastic strategy.

Entry Long: RSI < 30 + Stochastic < 20 + EMA20 > EMA50
Entry Short: RSI > 70 + Stochastic > 80 + EMA20 < EMA50
Exit: RSI flip or SL 2xATR

Output: JSON with entries and exits.
"""
import json
import pickle
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).parent))
from config import (
    PAIRS, SYMBOL_MAP, EMA_FAST, EMA_SLOW, RSI_PERIOD, 
    RSI_OVERSOLD, RSI_OVERBOUGHT, STOCH_PERIOD, 
    STOCH_OVERSOLD, STOCH_OVERBOUGHT, ATR_PERIOD, SL_ATR_MULTIPLIER
)


def load_candles():
    """Load candles from pickle."""
    pkl_path = Path(__file__).parent.parent / "data" / "candles.pkl"
    with open(pkl_path, "rb") as f:
        return pickle.load(f)


def calculate_rsi(close, period=14):
    """Calculate RSI."""
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = -delta.where(delta < 0, 0).rolling(period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_stochastic(high, low, close, period=14):
    """Calculate Stochastic %K."""
    low_min = low.rolling(period).min()
    high_max = high.rolling(period).max()
    stoch = 100 * (close - low_min) / (high_max - low_min)
    return stoch


def calculate_atr(high, low, close, period=14):
    """Calculate ATR."""
    tr1 = high - low
    tr2 = np.abs(high - close.shift(1))
    tr3 = np.abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    return atr


def generate_signals(save=True):
    """
    Generate entry and exit signals for all pairs.
    
    Returns:
        dict: {
            "timestamp": ISO timestamp,
            "entries": [{"symbol": ..., "side": "long"/"short", "atr": ..., "sl_distance": ...}],
            "exits": [{"symbol": ..., "reason": "rsi_flip"}]
        }
    """
    print("=" * 70)
    print("RSI + EMA + Stochastic — Signal Generation")
    print(f"Entry: RSI<{RSI_OVERSOLD} + Stoch<{STOCH_OVERSOLD} + EMA{EMA_FAST}>{EMA_SLOW} (long)")
    print(f"       RSI>{RSI_OVERBOUGHT} + Stoch>{STOCH_OVERBOUGHT} + EMA{EMA_FAST}<{EMA_SLOW} (short)")
    print("=" * 70)
    
    candles = load_candles()
    print(f"\nLoaded {len(candles)} pairs")
    
    entries = []
    exits = []
    
    for pair in PAIRS:
        if pair not in candles:
            continue
        
        bars = candles[pair]
        df = pd.DataFrame(bars)
        
        # Calculate indicators
        df["ema_fast"] = df["close"].ewm(span=EMA_FAST, adjust=False).mean()
        df["ema_slow"] = df["close"].ewm(span=EMA_SLOW, adjust=False).mean()
        df["rsi"] = calculate_rsi(df["close"], RSI_PERIOD)
        df["stoch"] = calculate_stochastic(df["high"], df["low"], df["close"], STOCH_PERIOD)
        df["atr"] = calculate_atr(df["high"], df["low"], df["close"], ATR_PERIOD)
        
        # Get latest 2 bars
        if len(df) < 2:
            continue
        
        prev = df.iloc[-2]
        curr = df.iloc[-1]
        
        # Check for exit (RSI flip from current positions - placeholder, will be checked in execute_strategy)
        # Exits are handled live by execute_strategy based on current positions
        
        # Check for entry
        if not pd.isna(curr["rsi"]) and not pd.isna(curr["stoch"]):
            # Long: RSI oversold + Stoch oversold + EMA uptrend
            if curr["rsi"] < RSI_OVERSOLD and curr["stoch"] < STOCH_OVERSOLD and curr["ema_fast"] > curr["ema_slow"]:
                entries.append({
                    "symbol": pair,
                    "side": "long",
                    "atr": float(curr["atr"]),
                    "sl_distance": float(curr["atr"] * SL_ATR_MULTIPLIER),
                    "rsi": float(curr["rsi"]),
                    "stoch": float(curr["stoch"]),
                    "close": float(curr["close"]),
                })
            
            # Short: RSI overbought + Stoch overbought + EMA downtrend
            elif curr["rsi"] > RSI_OVERBOUGHT and curr["stoch"] > STOCH_OVERBOUGHT and curr["ema_fast"] < curr["ema_slow"]:
                entries.append({
                    "symbol": pair,
                    "side": "short",
                    "atr": float(curr["atr"]),
                    "sl_distance": float(curr["atr"] * SL_ATR_MULTIPLIER),
                    "rsi": float(curr["rsi"]),
                    "stoch": float(curr["stoch"]),
                    "close": float(curr["close"]),
                })
    
    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "entries": entries,
        "exits": exits,
    }
    
    print(f"\n[Signal Summary]")
    print(f"  Entries: {len(entries)} ({sum(1 for e in entries if e['side']=='long')} long, {sum(1 for e in entries if e['side']=='short')} short)")
    
    if entries:
        print("\n[Entry Signals]")
        for e in entries[:10]:
            print(f"  {e['side'].upper():5} {e['symbol']:10} RSI={e['rsi']:.1f} Stoch={e['stoch']:.1f} SL={e['sl_distance']:.5f}")
    
    if save:
        out_path = Path(__file__).parent.parent / "output" / "signal_latest.json"
        out_path.parent.mkdir(exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(result, f, indent=2)
        print(f"\nSaved: {out_path}")
    
    return result


if __name__ == "__main__":
    generate_signals()
