import numpy as np
import pandas as pd

def calculate_atr_pine(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 10) -> pd.Series:
    """True Range smoothed via RMA (Wilder's smoothing) matching Pine Script ta.atr / ta.rma."""
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / length, adjust=False).mean()

def calculate_supertrend_pine(df: pd.DataFrame, factor: float = 3.0, length: int = 10) -> pd.DataFrame:
    """
    Standard Pine Script ta.supertrend(factor, length):
    hl2 = (high + low) / 2.0
    basic_upper = hl2 + factor * atr
    basic_lower = hl2 - factor * atr
    """
    high = df['high']
    low = df['low']
    close = df['close']
    
    atr = calculate_atr_pine(high, low, close, length)
    hl2 = (high + low) / 2.0
    
    basic_upper = (hl2 + factor * atr).to_numpy()
    basic_lower = (hl2 - factor * atr).to_numpy()
    close_vals = close.to_numpy()
    n = len(df)
    
    final_upper = np.zeros(n)
    final_lower = np.zeros(n)
    supertrend = np.zeros(n)
    direction = np.zeros(n) # -1 = uptrend (green), 1 = downtrend (red)
    
    final_upper[0] = basic_upper[0]
    final_lower[0] = basic_lower[0]
    direction[0] = 1
    supertrend[0] = final_upper[0]
    
    for i in range(1, n):
        # Lower band
        if basic_lower[i] > final_lower[i-1] or close_vals[i-1] < final_lower[i-1]:
            final_lower[i] = basic_lower[i]
        else:
            final_lower[i] = final_lower[i-1]
            
        # Upper band
        if basic_upper[i] < final_upper[i-1] or close_vals[i-1] > final_upper[i-1]:
            final_upper[i] = basic_upper[i]
        else:
            final_upper[i] = final_upper[i-1]
            
        # Direction & Supertrend
        if direction[i-1] == 1:
            if close_vals[i] > final_upper[i-1]:
                direction[i] = -1
                supertrend[i] = final_lower[i]
            else:
                direction[i] = 1
                supertrend[i] = final_upper[i]
        else:
            if close_vals[i] < final_lower[i-1]:
                direction[i] = 1
                supertrend[i] = final_upper[i]
            else:
                direction[i] = -1
                supertrend[i] = final_lower[i]
                
    return pd.DataFrame({
        "atr": atr,
        "supertrend": supertrend,
        "direction": direction,
        "st_up": final_lower,
        "st_dn": final_upper
    }, index=df.index)

def calculate_indicators(df: pd.DataFrame, factor: float = 3.0, atr_len: int = 10, pivot_len: int = 20, rwi_len: int = 10) -> pd.DataFrame:
    """Exact replication of Pine Script 'SuperRWI Bot Visual [BETA]'."""
    df = df.copy()
    
    st_df = calculate_supertrend_pine(df, factor=factor, length=atr_len)
    df = pd.concat([df, st_df], axis=1)
    
    # Resistance & Support Pivots (20 bars)
    df['pHigh'] = df['high'].rolling(pivot_len).max()
    df['pLow'] = df['low'].rolling(pivot_len).min()
    
    # RWI formula from Pine: (ta.highest(high, 10) - ta.lowest(low, 10)) / (ta.atr(atrLen) * math.sqrt(10))
    df['rwiVal'] = (df['high'].rolling(rwi_len).max() - df['low'].rolling(rwi_len).min()) / (df['atr'] * np.sqrt(rwi_len))
    
    # Near S&R conditions
    df['nearRes'] = df['close'] > (df['pHigh'] * 0.999)
    df['nearSup'] = df['close'] < (df['pLow'] * 1.001)
    
    # Crossover & Crossunder (Flip triggers)
    df['crossover'] = (df['direction'].shift(1) == 1) & (df['direction'] == -1)
    df['crossunder'] = (df['direction'].shift(1) == -1) & (df['direction'] == 1)
    
    return df
