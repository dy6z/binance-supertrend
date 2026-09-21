
import pandas as pd
import numpy as np
from src.indicators import calculate_indicators

# This master script ensures absolute determinism.
symbols = ["ETH", "SOL", "ZEC", "SNDK", "BCH", "AAVE"]
print(f"{'Symbol':<8} {'Trades':<8} {'Return':<10}")

for sym in symbols:
    try:
        # ALWAYS load the EXACT same CSV file
        df = pd.read_csv(f"/home/dy6z/workspace/binance-supertrend/data_{sym}.csv")
        df = calculate_indicators(df)
        
        capital = 100
        trades = 0
        position = 0
        entry_price = 0
        
        # Start from index 100 to ensure indicators are fully initialized
        for i in range(100, len(df)):
            close = df["close"].iloc[i]
            crossover_dn = (close > df["st_dn"].iloc[i]) and (df["close"].iloc[i-1] <= df["st_dn"].iloc[i-1])
            crossunder_up = (close < df["st_up"].iloc[i]) and (df["close"].iloc[i-1] >= df["st_up"].iloc[i-1])
            
            # Flip Logic
            if position == 0:
                if crossover_dn and close > df["ema"].iloc[i] and df["rwi_high"].iloc[i] >= 1.0:
                    position, entry_price, trades = 1, close, trades + 1
                elif crossunder_up and close < df["ema"].iloc[i] and df["rwi_low"].iloc[i] >= 1.0:
                    position, entry_price, trades = -1, close, trades + 1
            elif position == 1 and crossunder_up:
                capital += (close - entry_price)
                position = 0
            elif position == -1 and crossover_dn:
                capital += (entry_price - close)
                position = 0
        
        print(f"{sym:<8} {trades:<8} {(capital-100):.2f}%")
    except Exception as e:
        print(f"{sym:<8} Error: {e}")
