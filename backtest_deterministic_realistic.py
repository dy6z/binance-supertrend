
import pandas as pd
import numpy as np
from src.indicators import calculate_indicators

def run_realistic_backtest():
    symbols = ["ETH", "ZEC", "SNDK", "BCH", "AAVE", "SOL"]
    
    print(f"{'Symbol':<8} {'Trades':<8} {'Return (Realistic)':<20}")
    
    fee_rate = 0.0005 # 0.05%
    slippage = 0.0002 # 0.02%
    
    for sym in symbols:
        try:
            df = pd.read_csv(f"/home/dy6z/workspace/binance-supertrend/data_{sym}.csv")
            df = calculate_indicators(df)
            
            trades = 0
            capital = 100
            position = 0
            entry_price = 0
            
            for i in range(50, len(df)):
                close = df["close"].iloc[i]
                crossover_dn = (df["close"].iloc[i] > df["st_dn"].iloc[i]) and (df["close"].iloc[i-1] <= df["st_dn"].iloc[i-1])
                crossunder_up = (df["close"].iloc[i] < df["st_up"].iloc[i]) and (df["close"].iloc[i-1] >= df["st_up"].iloc[i-1])
                
                # Entry (Long/Short)
                if crossover_dn and df["close"].iloc[i] > df["ema"].iloc[i] and df["rwi_high"].iloc[i] >= 1.0 and position <= 0:
                    if position == -1: 
                        # Exit Short
                        capital -= (entry_price - close) # Profit/loss
                        capital -= (capital * (fee_rate + slippage)) # Apply fee/slippage
                    position = 1
                    entry_price = close * (1 + slippage) # Apply slippage on entry
                    trades += 1
                    capital -= (capital * fee_rate)
                    
                elif crossunder_up and df["close"].iloc[i] < df["ema"].iloc[i] and df["rwi_low"].iloc[i] >= 1.0 and position >= 0:
                    if position == 1: 
                        # Exit Long
                        capital += (close - entry_price)
                        capital -= (capital * (fee_rate + slippage))
                    position = -1
                    entry_price = close * (1 - slippage)
                    trades += 1
                    capital -= (capital * fee_rate)
            
            print(f"{sym:<8} {trades:<8} {(capital-100):.2f}%")
        except Exception as e:
            print(f"{sym:<8} Error: {e}")

run_realistic_backtest()
