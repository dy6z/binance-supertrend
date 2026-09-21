#!/usr/bin/env python3.12
"""
Calculate Supertrend + ADX indicators for FX pairs.

Supertrend:
- Based on ATR bands around HL/2
- Direction: +1 (bullish), -1 (bearish)

ADX (Average Directional Index):
- Measures trend strength (0-100)
- >25 = strong trend
- Does NOT indicate direction (use +DI/-DI or Supertrend for that)
"""
import numpy as np
import pandas as pd


def calculate_atr(high, low, close, period=14):
    """Calculate Average True Range."""
    tr1 = high - low
    tr2 = np.abs(high - close.shift(1))
    tr3 = np.abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    return atr


def calculate_supertrend(high, low, close, period=10, multiplier=3.0):
    """
    Calculate Supertrend indicator.
    
    Returns:
        pd.DataFrame with columns: supertrend, direction
        - supertrend: the band value
        - direction: +1 (bullish), -1 (bearish)
    """
    atr = calculate_atr(high, low, close, period)
    hl2 = (high + low) / 2
    
    # Basic bands
    upperband = hl2 + (multiplier * atr)
    lowerband = hl2 - (multiplier * atr)
    
    # Initialize
    supertrend = pd.Series(index=close.index, dtype=float)
    direction = pd.Series(index=close.index, dtype=float)
    
    for i in range(period, len(close)):
        if i == period:
            supertrend.iloc[i] = upperband.iloc[i]
            direction.iloc[i] = -1
        else:
            prev_st = supertrend.iloc[i-1]
            prev_dir = direction.iloc[i-1]
            
            # Update bands
            if close.iloc[i-1] <= prev_st:
                # Was bearish, check lowerband
                if lowerband.iloc[i] < prev_st:
                    lowerband.iloc[i] = prev_st
            else:
                # Was bullish, check upperband
                if upperband.iloc[i] > prev_st:
                    upperband.iloc[i] = prev_st
            
            # Determine current supertrend
            if close.iloc[i] <= lowerband.iloc[i]:
                supertrend.iloc[i] = lowerband.iloc[i]
                direction.iloc[i] = -1
            elif close.iloc[i] >= upperband.iloc[i]:
                supertrend.iloc[i] = upperband.iloc[i]
                direction.iloc[i] = 1
            else:
                # No change
                supertrend.iloc[i] = prev_st
                direction.iloc[i] = prev_dir
    
    return pd.DataFrame({"supertrend": supertrend, "direction": direction})


def calculate_adx(high, low, close, period=14):
    """
    Calculate ADX (Average Directional Index).
    
    Returns value 0-100 indicating trend strength.
    """
    # Directional movement
    up = high.diff()
    down = -low.diff()
    
    plus_dm = np.where((up > down) & (up > 0), up, 0)
    minus_dm = np.where((down > up) & (down > 0), down, 0)
    
    # True range
    tr1 = high - low
    tr2 = np.abs(high - close.shift(1))
    tr3 = np.abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # Smooth with Wilder's MA
    atr = tr.ewm(alpha=1/period, adjust=False).mean()
    plus_di = 100 * pd.Series(plus_dm).ewm(alpha=1/period, adjust=False).mean() / atr
    minus_di = 100 * pd.Series(minus_dm).ewm(alpha=1/period, adjust=False).mean() / atr
    
    # DX
    dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
    
    # ADX (smooth DX)
    adx = dx.ewm(alpha=1/period, adjust=False).mean()
    
    return adx


def calculate_indicators(df, supertrend_period=10, supertrend_mult=3.0, 
                        adx_period=14, atr_period=14):
    """
    Calculate all indicators for a single pair.
    
    Args:
        df: DataFrame with columns [open, high, low, close, timestamp]
        
    Returns:
        DataFrame with added columns: supertrend, st_direction, adx, atr
    """
    df = df.copy()
    
    # Supertrend
    st = calculate_supertrend(df["high"], df["low"], df["close"], 
                              supertrend_period, supertrend_mult)
    df["supertrend"] = st["supertrend"]
    df["st_direction"] = st["direction"]
    
    # ADX
    df["adx"] = calculate_adx(df["high"], df["low"], df["close"], adx_period)
    
    # ATR (for stop loss sizing)
    df["atr"] = calculate_atr(df["high"], df["low"], df["close"], atr_period)
    
    return df


if __name__ == "__main__":
    # Test with synthetic data
    dates = pd.date_range("2020-01-01", periods=200, freq="D")
    np.random.seed(42)
    close = 100 + np.cumsum(np.random.randn(200) * 0.5)
    high = close + np.random.rand(200) * 2
    low = close - np.random.rand(200) * 2
    
    df = pd.DataFrame({
        "timestamp": dates,
        "open": close,
        "high": high,
        "low": low,
        "close": close,
    })
    
    result = calculate_indicators(df)
    print(result.tail(10))
    print("\nIndicators calculated:")
    print(f"  Supertrend: {result['supertrend'].iloc[-1]:.2f}")
    print(f"  Direction: {result['st_direction'].iloc[-1]:.0f} ({'bullish' if result['st_direction'].iloc[-1] > 0 else 'bearish'})")
    print(f"  ADX: {result['adx'].iloc[-1]:.1f}")
    print(f"  ATR: {result['atr'].iloc[-1]:.2f}")
