
import pandas as pd
import numpy as np
from src.binance_client import BinanceFuturesClient
from src.indicators import calculate_indicators

def run_multi_backtest():
    client = BinanceFuturesClient(sandbox=False)
    symbols = ["BTC/USDT:USDT", "ETH/USDT:USDT", "SOL/USDT:USDT", "ZEC/USDT:USDT"]
    
    for symbol in symbols:
        df = client.fetch_ohlcv_df(symbol, timeframe="15m", limit=1000)
        df = calculate_indicators(df)
        
        capital = 100
        position = 0 # 1 long, -1 short
        entry_price = 0.0
        trades = 0
        
        for i in range(50, len(df)):
            close = df['close'].iloc[i]
            crossover_dn = (df['close'].iloc[i] > df['st_dn'].iloc[i]) and (df['close'].iloc[i-1] <= df['st_dn'].iloc[i-1])
            crossunder_up = (df['close'].iloc[i] < df['st_up'].iloc[i]) and (df['close'].iloc[i-1] >= df['st_up'].iloc[i-1])
            
            if crossover_dn and df['close'].iloc[i] > df['ema'].iloc[i] and df['rwi_high'].iloc[i] >= 1.0 and position <= 0:
                if position == -1: capital += (entry_price - close)
                position = 1
                entry_price = close
                trades += 1
            elif crossunder_up and df['close'].iloc[i] < df['ema'].iloc[i] and df['rwi_low'].iloc[i] >= 1.0 and position >= 0:
                if position == 1: capital += (close - entry_price)
                position = -1
                entry_price = close
                trades += 1
                
        print(f"{symbol.split('/')[0]}: Trades={trades}, Return={(capital-100):.2f}%")

run_multi_backtest()
