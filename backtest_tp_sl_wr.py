
import pandas as pd
import numpy as np
from src.indicators import calculate_indicators

def run_wr_backtest():
    symbols = ["ETH", "ZEC", "SNDK", "SOL", "BCH", "AAVE"]
    print(f"{'Symbol':<8} {'Trades':<8} {'Wins':<8} {'WR (%)':<8} {'Return':<10}")
    
    fee_rate, slippage = 0.0005, 0.0002
    tp_mult, sl_mult = 1.4, 0.4
    
    for sym in symbols:
        try:
            df = pd.read_csv(f"/home/dy6z/workspace/binance-supertrend/data_{sym}.csv")
            df = calculate_indicators(df)
            
            capital, trades, wins, position = 100, 0, 0, 0
            entry_price, tp_level, sl_level = 0.0, 0.0, 0.0
            
            for i in range(100, len(df)):
                close, high, low = df["close"].iloc[i], df["high"].iloc[i], df["low"].iloc[i]
                
                # EXIT (TP/SL)
                if position != 0:
                    exit_reason = None # 'tp' or 'sl'
                    if position == 1: # Long
                        if high >= tp_level: exit_reason = 'tp'
                        elif low <= sl_level: exit_reason = 'sl'
                    elif position == -1: # Short
                        if low <= tp_level: exit_reason = 'tp'
                        elif high >= sl_level: exit_reason = 'sl'
                    
                    if exit_reason:
                        if exit_reason == 'tp':
                            capital += (abs(tp_level - entry_price)) - (capital * (fee_rate + slippage))
                            wins += 1
                        else:
                            capital -= (abs(sl_level - entry_price)) + (capital * (fee_rate + slippage))
                        position = 0
                
                # ENTRY (Logic)
                if position == 0:
                    crossover_dn = (df["close"].iloc[i] > df["st_dn"].iloc[i]) and (df["close"].iloc[i-1] <= df["st_dn"].iloc[i-1])
                    crossunder_up = (df["close"].iloc[i] < df["st_up"].iloc[i]) and (df["close"].iloc[i-1] >= df["st_up"].iloc[i-1])
                    atr = (df["high"].iloc[i] - df["low"].iloc[i])
                    
                    if crossover_dn and df["close"].iloc[i] > df["ema"].iloc[i] and df["rwi_high"].iloc[i] >= 1.0:
                        position = 1
                        entry_price = close * (1 + slippage)
                        tp_level = entry_price + (atr * tp_mult)
                        sl_level = entry_price - (atr * sl_mult)
                        trades += 1
                        capital -= (capital * fee_rate)
                    elif crossunder_up and df["close"].iloc[i] < df["ema"].iloc[i] and df["rwi_low"].iloc[i] >= 1.0:
                        position = -1
                        entry_price = close * (1 - slippage)
                        tp_level = entry_price - (atr * tp_mult)
                        sl_level = entry_price + (atr * sl_mult)
                        trades += 1
                        capital -= (capital * fee_rate)
            
            wr = (wins / trades * 100) if trades > 0 else 0
            print(f"{sym:<8} {trades:<8} {wins:<8} {wr:<8.2f} {(capital-100):.2f}%")
        except Exception as e:
            print(f"{sym:<8} Error: {e}")

run_wr_backtest()
