import pandas as pd
from src.indicators import calculate_indicators, calculate_atr_pine

symbols = ["ETH", "SOL", "ZEC", "SNDK", "BCH", "AAVE"]
print(f"{'Symbol':<8} {'Trades':<8} {'WR (%)':<8} {'Return':<10}")

fee_rate, slippage = 0.0005, 0.0002
tp_mult, sl_mult = 1.4, 0.4

for sym in symbols:
    try:
        df = pd.read_csv(f"/home/dy6z/workspace/binance-supertrend/data_{sym}.csv")
        df = calculate_indicators(df)
        atr = calculate_atr_pine(df['high'], df['low'], df['close'], 14)
        
        capital, trades, wins, position = 100, 0, 0, 0
        entry_price, tp_level, sl_level = 0.0, 0.0, 0.0
        
        for i in range(100, len(df)):
            close, high, low = df["close"].iloc[i], df["high"].iloc[i], df["low"].iloc[i]
            current_atr = atr.iloc[i]
            
            if position != 0:
                exit_reason = None
                if position == 1:
                    if high >= tp_level: exit_reason = 'tp'
                    elif low <= sl_level: exit_reason = 'sl'
                elif position == -1:
                    if low <= tp_level: exit_reason = 'tp'
                    elif high >= sl_level: exit_reason = 'sl'
                
                if exit_reason:
                    if exit_reason == 'tp':
                        capital += (abs(tp_level - entry_price)) - (capital * (fee_rate + slippage))
                        wins += 1
                    else:
                        capital -= (abs(sl_level - entry_price)) + (capital * (fee_rate + slippage))
                    position = 0
            
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
