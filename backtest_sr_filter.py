
import pandas as pd
import numpy as np
from src.indicators import calculate_indicators

symbols = ["ETH", "SOL", "ZEC", "SNDK"]
print(f"Backtest: SuperRWI + Pivot Filter (20-bar)")
print(f"{'Symbol':<8} {'Trades':<8} {'Return':<10}")

for sym in symbols:
    try:
        df = pd.read_csv(f"/home/dy6z/workspace/binance-supertrend/data_{sym}.csv")
        df = calculate_indicators(df)
        
        # Calculate Pivots (local high/low in last 20 bars)
        df['pivot_high'] = df['high'].rolling(window=20, center=True).max()
        df['pivot_low'] = df['low'].rolling(window=20, center=True).min()
        
        capital, trades, position, entry_price = 100, 0, 0, 0
        
        for i in range(100, len(df)):
            close = df["close"].iloc[i]
            crossover_dn = (close > df["st_dn"].iloc[i]) and (df["close"].iloc[i-1] <= df["st_dn"].iloc[i-1])
            crossunder_up = (close < df["st_up"].iloc[i]) and (df["close"].iloc[i-1] >= df["st_up"].iloc[i-1])
            
            # S&R Pivot Filtering
            # Long: Don't buy if price is near a pivot high (Resistance)
            # Short: Don't sell if price is near a pivot low (Support)
            near_resistance = close > (df['pivot_high'].iloc[i] * 0.995)
            near_support = close < (df['pivot_low'].iloc[i] * 1.005)
            
            if position == 0:
                if crossover_dn and close > df["ema"].iloc[i] and df["rwi_high"].iloc[i] >= 1.0 and not near_resistance:
                    position, entry_price, trades = 1, close, trades + 1
                elif crossunder_up and close < df["ema"].iloc[i] and df["rwi_low"].iloc[i] >= 1.0 and not near_support:
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
