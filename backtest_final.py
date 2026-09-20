
import pandas as pd
import numpy as np
from src.binance_client import BinanceFuturesClient
from datetime import time

def get_rma(series, length):
    return series.ewm(alpha=1/length, adjust=False).mean()

def calculate_supertrend_pine(df, factor=2.0, length=14):
    atr = get_rma(pd.concat([df['high']-df['low'], np.abs(df['high']-df['close'].shift(1)), np.abs(df['low']-df['close'].shift(1))], axis=1).max(axis=1), length)
    up = df['close'] - (factor * atr)
    dn = df['close'] + (factor * atr)
    
    # Use lists to be mutable
    st_up = up.copy().tolist()
    st_dn = dn.copy().tolist()
    up_vals = up.values
    dn_vals = dn.values
    close_vals = df['close'].values
    trend = np.ones(len(df))
    
    for i in range(1, len(df)):
        st_up[i] = max(up_vals[i], st_up[i-1]) if close_vals[i-1] > st_up[i-1] else up_vals[i]
        st_dn[i] = min(dn_vals[i], st_dn[i-1]) if close_vals[i-1] < st_dn[i-1] else dn_vals[i]
        
        if trend[i-1] == -1 and close_vals[i] > st_dn[i]: trend[i] = 1
        elif trend[i-1] == 1 and close_vals[i] < st_up[i]: trend[i] = -1
        else: trend[i] = trend[i-1]
        
    return pd.DataFrame({"st_up": st_up, "st_dn": st_dn, "st_trend": trend}, index=df.index)

def run_backtest():
    client = BinanceFuturesClient(sandbox=False)
    # ETH 4H Data
    df = client.fetch_ohlcv_df("ETH/USDT:USDT", timeframe="4h", limit=1000)
    df.index = pd.to_datetime(df['timestamp'], unit='ms')
    
    # Parameters (Pine default)
    Periods, Multiplier = 14, 2.0
    RWlength, RWTrigger = 5, 1.0
    EMALen = 50
    
    # Indicators
    st_df = calculate_supertrend_pine(df, Multiplier, Periods)
    df['st_up'], df['st_dn'], df['st_trend'] = st_df['st_up'], st_df['st_dn'], st_df['st_trend']
    df['ema'] = df['close'].ewm(span=EMALen, adjust=False).mean()
    atr = get_rma(pd.concat([df['high']-df['low'], np.abs(df['high']-df['close'].shift(1)), np.abs(df['low']-df['close'].shift(1))], axis=1).max(axis=1), 14)
    
    df['rwi_high'] = (df['high'] - df['low'].shift(RWlength)) / (atr * np.sqrt(RWlength))
    df['rwi_low'] = (df['high'].shift(RWlength) - df['low']) / (atr * np.sqrt(RWlength))
    
    capital = 1000
    position = 0 # 1 long, -1 short
    entry_price = 0.0
    trades = 0
    
    # Run simulation without Trading Window restriction for ETH 4H
    for i in range(50, len(df)):
        close = df['close'].iloc[i]
        
        crossover_dn = (df['close'].iloc[i] > df['st_dn'].iloc[i]) and (df['close'].iloc[i-1] <= df['st_dn'].iloc[i-1])
        crossunder_up = (df['close'].iloc[i] < df['st_up'].iloc[i]) and (df['close'].iloc[i-1] >= df['st_up'].iloc[i-1])
        
        long_entry = crossover_dn and (df['close'].iloc[i] > df['ema'].iloc[i]) and (df['rwi_high'].iloc[i] >= RWTrigger)
        short_entry = crossunder_up and (df['close'].iloc[i] < df['ema'].iloc[i]) and (df['rwi_low'].iloc[i] >= RWTrigger)
        
        if long_entry and position <= 0:
            if position == -1: capital += (entry_price - close)
            position = 1
            entry_price = close
            trades += 1
        elif short_entry and position >= 0:
            if position == 1: capital += (close - entry_price)
            position = -1
            entry_price = close
            trades += 1
                
    print(f"Backtest Results (ETH/USDT 4H, SuperRWI):")
    print(f"Total Trades: {trades}")
    print(f"Final Capital: {capital:.2f}")

run_backtest()
