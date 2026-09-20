
import pandas as pd
import numpy as np
from src.indicators import calculate_indicators

def run_honest_backtest():
    symbols = ["ETH", "ZEC", "SNDK", "SOL"]
    
    print(f"{'Symbol':<8} {'Trades':<8} {'WR (%)':<8} {'Return (Final)':<15}")
    
    fee_rate = 0.0005 # 0.05%
    slippage = 0.0002 # 0.02%
    tp_pct = 0.011 # 1.1%
    sl_pct = 0.007 # 0.7%
    
    for sym in symbols:
        try:
            df = pd.read_csv(f"/home/dy6z/workspace/binance-supertrend/data_{sym}.csv")
            df = calculate_indicators(df)
            
            capital = 100
            trades = 0
            wins = 0
            position = 0 # 0 none, 1 long, -1 short
            entry_price = 0
            
            for i in range(50, len(df)):
                close = df["close"].iloc[i]
                high = df["high"].iloc[i]
                low = df["low"].iloc[i]
                
                # Exit Logic (TP/SL)
                if position == 1:
                    tp_price = entry_price * (1 + tp_pct)
                    sl_price = entry_price * (1 - sl_pct)
                    if high >= tp_price:
                        capital += (capital * tp_pct)
                        capital -= (capital * (fee_rate + slippage))
                        position = 0
                        wins += 1
                    elif low <= sl_price:
                        capital -= (capital * sl_pct)
                        capital -= (capital * (fee_rate + slippage))
                        position = 0
                elif position == -1:
                    tp_price = entry_price * (1 - tp_pct)
                    sl_price = entry_price * (1 + sl_pct)
                    if low <= tp_price:
                        capital += (capital * tp_pct)
                        capital -= (capital * (fee_rate + slippage))
                        position = 0
                        wins += 1
                    elif high >= sl_price:
                        capital -= (capital * sl_pct)
                        capital -= (capital * (fee_rate + slippage))
                        position = 0

                # Entry Logic
                if position == 0:
                    crossover_dn = (df["close"].iloc[i] > df["st_dn"].iloc[i]) and (df["close"].iloc[i-1] <= df["st_dn"].iloc[i-1])
                    crossunder_up = (df["close"].iloc[i] < df["st_up"].iloc[i]) and (df["close"].iloc[i-1] >= df["st_up"].iloc[i-1])
                    
                    if crossover_dn and df["close"].iloc[i] > df["ema"].iloc[i] and df["rwi_high"].iloc[i] >= 1.0:
                        position = 1
                        entry_price = close * (1 + slippage)
                        trades += 1
                        capital -= (capital * fee_rate)
                    elif crossunder_up and df["close"].iloc[i] < df["ema"].iloc[i] and df["rwi_low"].iloc[i] >= 1.0:
                        position = -1
                        entry_price = close * (1 - slippage)
                        trades += 1
                        capital -= (capital * fee_rate)
            
            wr = (wins / trades * 100) if trades > 0 else 0
            print(f"{sym:<8} {trades:<8} {wr:<8.2f} {(capital-100):.2f}%")
        except Exception as e:
            print(f"{sym:<8} Error: {e}")

run_honest_backtest()
