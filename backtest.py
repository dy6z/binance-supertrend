
import pandas as pd
import numpy as np
from src.binance_client import BinanceFuturesClient

def calculate_atr(high, low, close, length=14):
    tr = pd.concat([high-low, np.abs(high-close.shift(1)), np.abs(low-close.shift(1))], axis=1).max(axis=1)
    return tr.rolling(length).mean()

def run_backtest():
    client = BinanceFuturesClient(sandbox=False)
    # ETH 4H Data
    df = client.fetch_ohlcv_df("ETH/USDT:USDT", timeframe="4h", limit=1000)
    
    # 1. EMA 50
    df['ema'] = df['close'].ewm(span=50).mean()
    
    # 2. SuperTrend 14 (14 ATR) - Pine Script 'Periods=14, Multiplier=2.0'
    atr = calculate_atr(df['high'], df['low'], df['close'], 14)
    up = df['close'] - (2.0 * atr)
    dn = df['close'] + (2.0 * atr)
    
    st_dir = pd.Series(1, index=df.index)
    for i in range(1, len(df)):
        if df['close'].iloc[i-1] > up.iloc[i-1]: up.iloc[i] = max(up.iloc[i], up.iloc[i-1])
        if df['close'].iloc[i-1] < dn.iloc[i-1]: dn.iloc[i] = min(dn.iloc[i], dn.iloc[i-1])
        if st_dir.iloc[i-1] == -1 and df['close'].iloc[i] > dn.iloc[i]: st_dir.iloc[i] = 1
        elif st_dir.iloc[i-1] == 1 and df['close'].iloc[i] < up.iloc[i]: st_dir.iloc[i] = -1
        else: st_dir.iloc[i] = st_dir.iloc[i-1]

    # 3. RWI (5 period lookback)
    atr_rwi = calculate_atr(df['high'], df['low'], df['close'], 5)
    df['rwi_high'] = (df['high'] - df['low'].shift(5)) / (atr_rwi * np.sqrt(5))
    df['rwi_low'] = (df['high'].shift(5) - df['low']) / (atr_rwi * np.sqrt(5))
    
    # 4. ADX (14 period)
    plus_dm = (df['high'] - df['high'].shift(1)).clip(lower=0)
    minus_dm = (df['low'].shift(1) - df['low']).clip(lower=0)
    tr = calculate_atr(df['high'], df['low'], df['close'], 14)
    plus_di = 100 * (plus_dm.ewm(span=14).mean() / tr)
    minus_di = 100 * (minus_dm.ewm(span=14).mean() / tr)
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    df['adx'] = dx.ewm(span=14).mean()

    capital = 1000
    position = 0 # 1 long, -1 short
    entry_price = 0
    trades = 0
    
    # Strategy Logic (Pine script entry)
    # crossover(close, dn) -> close > dn and close.shift(1) <= dn.shift(1)
    for i in range(50, len(df)):
        # SuperTrend crossover detection (using Pine logic equivalent)
        crossover_dn = (df['close'].iloc[i-1] > dn.iloc[i-1]) and (df['close'].iloc[i-2] <= dn.iloc[i-2])
        crossunder_up = (df['close'].iloc[i-1] < up.iloc[i-1]) and (df['close'].iloc[i-2] >= up.iloc[i-2])
        
        long_entry = (crossover_dn) and (df['close'].iloc[i-1] > df['ema'].iloc[i-1]) and (df['rwi_high'].iloc[i-1] >= 1.0) and (df['adx'].iloc[i-1] >= 0)
        short_entry = (crossunder_up) and (df['close'].iloc[i-1] < df['ema'].iloc[i-1]) and (df['rwi_low'].iloc[i-1] >= 1.0) and (df['adx'].iloc[i-1] >= 0)
        
        if long_entry and position <= 0:
            if position == -1: capital += (entry_price - df['close'].iloc[i])
            position = 1
            entry_price = df['close'].iloc[i]
            trades += 1
        elif short_entry and position >= 0:
            if position == 1: capital += (df['close'].iloc[i] - entry_price)
            position = -1
            entry_price = df['close'].iloc[i]
            trades += 1
            
    print(f"Backtest Results (SuperRWI Pine Logic Ported):")
    print(f"Total Trades: {trades}")
    print(f"Final Capital: {capital:.2f}")

run_backtest()
