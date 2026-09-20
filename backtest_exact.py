
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
    
    # State tracking for Pine Script Supertrend
    st_up = up.copy()
    st_dn = dn.copy()
    trend = pd.Series(1, index=df.index)
    
    for i in range(1, len(df)):
        if df['close'].iloc[i-1] > st_up.iloc[i-1]: st_up.iloc[i] = max(up.iloc[i], st_up.iloc[i-1])
        if df['close'].iloc[i-1] < st_dn.iloc[i-1]: st_dn.iloc[i] = min(dn.iloc[i], st_dn.iloc[i-1])
        
        if trend.iloc[i-1] == -1 and df['close'].iloc[i] > st_dn.iloc[i]: trend.iloc[i] = 1
        elif trend.iloc[i-1] == 1 and df['close'].iloc[i] < st_up.iloc[i]: trend.iloc[i] = -1
        else: trend.iloc[i] = trend.iloc[i-1]
        
    return st_up, st_dn, trend

def run_backtest():
    client = BinanceFuturesClient(sandbox=False)
    df = client.fetch_ohlcv_df("BTC/USDT:USDT", timeframe="15m", limit=3000)
    df.index = pd.to_datetime(df['timestamp'], unit='ms')
    
    # Parameters
    Periods, Multiplier = 14, 2.0
    RWlength, RWTrigger = 5, 1.0
    EMALen = 50
    
    # Indicators
    st_up, st_dn, st_trend = calculate_supertrend_pine(df, Multiplier, Periods)
    df['ema'] = df['close'].ewm(span=EMALen, adjust=False).mean()
    atr = get_rma(pd.concat([df['high']-df['low'], np.abs(df['high']-df['close'].shift(1)), np.abs(df['low']-df['close'].shift(1))], axis=1).max(axis=1), 14)
    
    df['rwi_high'] = (df['high'] - df['low'].shift(RWlength)) / (atr * np.sqrt(RWlength))
    df['rwi_low'] = (df['high'].shift(RWlength) - df['low']) / (atr * np.sqrt(RWlength))
    
    # Trading window (0900-1330)
    def is_in_window(t):
        return time(9, 0) <= t.time() <= time(13, 30)
    
    # Backtest State Machine
    capital = 1000
    in_long, in_short = False, False
    long_tp, long_sl = 0.0, 0.0
    short_tp, short_sl = 0.0, 0.0
    entry_price = 0.0
    trades = 0
    
    for i in range(50, len(df)):
        close = df['close'].iloc[i]
        high = df['high'].iloc[i]
        low = df['low'].iloc[i]
        
        # Pine crossover detection (crossover(close, dn))
        crossover_dn = (close > st_dn.iloc[i]) and (df['close'].iloc[i-1] <= st_dn.iloc[i-1])
        crossunder_up = (close < st_up.iloc[i]) and (df['close'].iloc[i-1] >= st_up.iloc[i-1])
        
        # Entry Logic
        if not in_long and not in_short and is_in_window(df.index[i]):
            if crossover_dn and close > df['ema'].iloc[i] and df['rwi_high'].iloc[i] >= RWTrigger:
                in_long = True
                entry_price = close
                long_tp = close + (atr.iloc[i] * 1.4)
                long_sl = close - (atr.iloc[i] * 0.4)
                trades += 1
            elif crossunder_up and close < df['ema'].iloc[i] and df['rwi_low'].iloc[i] >= RWTrigger:
                in_short = True
                entry_price = close
                short_tp = close - (atr.iloc[i] * 1.4)
                short_sl = close + (atr.iloc[i] * 0.4)
                trades += 1
        
        # Exit Logic
        elif in_long:
            if high >= long_tp or low <= long_sl:
                capital += (long_tp - entry_price) if high >= long_tp else (long_sl - entry_price)
                in_long = False
        elif in_short:
            if low <= short_tp or high >= short_sl:
                capital += (entry_price - short_tp) if low <= short_tp else (entry_price - short_sl)
                in_short = False
                
    print(f"Final Capital: {capital:.2f}")
    print(f"Total Trades: {trades}")

run_backtest()
