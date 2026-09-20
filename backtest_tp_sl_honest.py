
import pandas as pd
import numpy as np
from src.indicators import calculate_indicators, calculate_atr_pine

def run_tp_sl_backtest():
    symbols = ["ETH", "ZEC", "SNDK", "BCH", "AAVE", "SOL"]
    
    print(f"{'Symbol':<8} {'Trades':<8} {'WR (%)':<8} {'Return (Final)':<15}")
    
    fee_rate = 0.0005 # 0.05%
    slippage = 0.0002 # 0.02%
    tp_mult = 1.4
    sl_mult = 0.4
    
    for sym in symbols:
        try:
            df = pd.read_csv(f"/home/dy6z/workspace/binance-supertrend/data_{sym}.csv")
            # Need fresh indicator calculation to include ATR
            df = calculate_indicators(df)
            atr = calculate_atr_pine(df['high'], df['low'], df['close'], 14)
            
            capital = 100
            trades = 0
            wins = 0
            position = 0
            entry_price = 0
            tp_level = 0
            sl_level = 0
            
            for i in range(50, len(df)):
                close = df["close"].iloc[i]
                high = df["high"].iloc[i]
                low = df["low"].iloc[i]
                current_atr = atr.iloc[i]
                
                # Exit Logic (TP/SL)
                if position != 0:
                    exit = False
                    if position == 1: # Long
                        if high >= tp_level:
                            capital += (tp_level - entry_price)
                            capital -= (capital * (fee_rate + slippage))
                            wins += 1
                            exit = True
                        elif low <= sl_level:
                            capital -= (entry_price - sl_level)
                            capital -= (capital * (fee_rate + slippage))
                            exit = True
                    elif position == -1: # Short
                        if low <= tp_level:
                            capital += (entry_price - tp_level)
                            capital -= (capital * (fee_rate + slippage))
                            wins += 1
                            exit = True
                        elif high >= sl_level:
                            capital -= (sl_level - entry_price)
                            capital -= (capital * (fee_rate + slippage))
                            exit = True
                    if exit: position = 0

                # Entry Logic
                if position == 0:
                    crossover_dn = (df["close"].iloc[i] > df["st_dn"].iloc[i]) and (df["close"].iloc[i-1] <= df["st_dn"].iloc[i-1])
                    crossunder_up = (df["close"].iloc[i] < df["st_up"].iloc[i]) and (df["close"].iloc[i-1] >= df["st_up"].iloc[i-1])
                    
                    if crossover_dn and df["close"].iloc[i] > df["ema"].iloc[i] and df["rwi_high"].iloc[i] >= 1.0:
                        position = 1
                        entry_price = close * (1 + slippage)
                        tp_level = entry_price + (current_atr * tp_mult)
                        sl_level = entry_price - (current_atr * sl_mult)
                        trades += 1
                        capital -= (capital * fee_rate)
                    elif crossunder_up and df["close"].iloc[i] < df["ema"].iloc[i] and df["rwi_low"].iloc[i] >= 1.0:
                        position = -1
                        entry_price = close * (1 - slippage)
                        tp_level = entry_price - (current_atr * tp_mult)
                        sl_level = entry_price + (current_atr * sl_mult)
                        trades += 1
                        capital -= (capital * fee_rate)
            
            wr = (wins / trades * 100) if trades > 0 else 0
            print(f"{sym:<8} {trades:<8} {wr:<8.2f} {(capital-100):.2f}%")
        except Exception as e:
            print(f"{sym:<8} Error: {e}")

run_tp_sl_backtest()
