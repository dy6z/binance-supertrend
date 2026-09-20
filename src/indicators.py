import numpy as np
import pandas as pd

def calculate_atr_pine(high, low, close, length=14):
    tr = pd.concat([high - low, np.abs(high - close.shift(1)), np.abs(low - close.shift(1))], axis=1).max(axis=1)
    return tr.ewm(alpha=1/length, adjust=False).mean()

def calculate_supertrend_pine(df, factor=2.0, length=14):
    atr = calculate_atr_pine(df['high'], df['low'], df['close'], length)
    up = (df['close'] - (factor * atr)).to_numpy()
    dn = (df['close'] + (factor * atr)).to_numpy()
    close_vals = df['close'].to_numpy()
    
    st_up = np.zeros(len(df))
    st_dn = np.zeros(len(df))
    trend = np.ones(len(df))
    
    st_up[0] = up[0]
    st_dn[0] = dn[0]
    
    for i in range(1, len(df)):
        st_up[i] = max(up[i], st_up[i-1]) if close_vals[i-1] > st_up[i-1] else up[i]
        st_dn[i] = min(dn[i], st_dn[i-1]) if close_vals[i-1] < st_dn[i-1] else dn[i]
        
        if trend[i-1] == -1 and close_vals[i] > st_dn[i]: trend[i] = 1
        elif trend[i-1] == 1 and close_vals[i] < st_up[i]: trend[i] = -1
        else: trend[i] = trend[i-1]
        
    return pd.DataFrame({"st_up": st_up, "st_dn": st_dn, "st_trend": trend}, index=df.index)

def calculate_indicators(df, period=14, multiplier=2.0, ema_len=50, rwi_len=5):
    df = df.copy()
    st = calculate_supertrend_pine(df, multiplier, period)
    df = pd.concat([df, st], axis=1)
    df["ema"] = df["close"].ewm(span=ema_len, adjust=False).mean()
    atr = calculate_atr_pine(df['high'], df['low'], df['close'], 14)
    df['rwi_high'] = (df['high'] - df['low'].shift(rwi_len)) / (atr * np.sqrt(rwi_len))
    df['rwi_low'] = (df['high'].shift(rwi_len) - df['low']) / (atr * np.sqrt(rwi_len))
    return df
