import pandas as pd
from src.indicators import calculate_indicators

symbols = ["ETH", "SOL", "ZEC", "SNDK", "BCH", "AAVE"]
print(f"{'Symbol':<8} {'Trades':<8} {'Return':<10}")

for sym in symbols:
    try:
        df = pd.read_csv(f"/home/dy6z/workspace/binance-supertrend/data_{sym}.csv")
        df = calculate_indicators(df)
        
        capital = 100
        trades, position, entry_price = 0, 0, 0
        
        for i in range(100, len(df)):
            close = df["close"].iloc[i]
            crossover_dn = (close > df["st_dn"].iloc[i]) and (df["close"].iloc[i-1] <= df["st_dn"].iloc[i-1])
            crossunder_up = (close < df["st_up"].iloc[i]) and (df["close"].iloc[i-1] >= df["st_up"].iloc[i-1])
            
            # Flip Logic (Exit only on signal)
            if position == 0:
                if crossover_dn and close > df["ema"].iloc[i] and df["rwi_high"].iloc[i] >= 1.0:
                    position, entry_price, trades = 1, close, trades + 1
                elif crossunder_up and close < df["ema"].iloc[i] and df["rwi_low"].iloc[i] >= 1.0:
                    position, entry_price, trades = -1, close, trades + 1
            elif position == 1 and crossunder_up: # Exit Long
                capital += (close - entry_price)
                position = 0
            elif position == -1 and crossover_dn: # Exit Short
                capital += (entry_price - close)
                position = 0
        
        print(f"{sym:<8} {trades:<8} {(capital-100):.2f}%")
    except Exception as e:
        print(f"{sym:<8} Error: {e}")
