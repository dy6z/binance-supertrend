
import pandas as pd
import numpy as np
from src.indicators import calculate_indicators

def run_deterministic_backtest():
    symbols = ["BTC", "ETH", "SOL", "ZEC", "SNDK", "HYPE", "XRP", "ARB", "UNI", "ENA"]
    
    print(f"{'Symbol':<8} {'Trades':<8} {'Return':<10}")
    
    for sym in symbols:
        try:
            # Load static data
            df = pd.read_csv(f"/home/dy6z/workspace/binance-supertrend/data_{sym}.csv")
            df = calculate_indicators(df)
            
            trades = 0
            capital = 100
            position = 0
            entry_price = 0
            
            # Logic: SuperRWI
            for i in range(50, len(df)):
                crossover_dn = (df['close'].iloc[i] > df['st_dn'].iloc[i]) and (df['close'].iloc[i-1] <= df['st_dn'].iloc[i-1])
                crossunder_up = (df['close'].iloc[i] < df['st_up'].iloc[i]) and (df['close'].iloc[i-1] >= df['st_up'].iloc[i-1])
                
                if crossover_dn and df['close'].iloc[i] > df['ema'].iloc[i] and df['rwi_high'].iloc[i] >= 1.0 and position <= 0:
                    if position == -1: capital += (entry_price - df['close'].iloc[i])
                    position = 1
                    entry_price = df['close'].iloc[i]
                    trades += 1
                elif crossunder_up and df['close'].iloc[i] < df['ema'].iloc[i] and df['rwi_low'].iloc[i] >= 1.0 and position >= 0:
                    if position == 1: capital += (df['close'].iloc[i] - entry_price)
                    position = -1
                    entry_price = df['close'].iloc[i]
                    trades += 1
            
            print(f"{sym:<8} {trades:<8} {(capital-100):.2f}%")
        except Exception as e:
            print(f"{sym:<8} Error: {e}")

run_deterministic_backtest()
