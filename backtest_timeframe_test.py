
import pandas as pd
import numpy as np
from src.indicators import calculate_indicators, calculate_atr_pine
from src.binance_client import BinanceFuturesClient

def run_tf_backtest(timeframe):
    client = BinanceFuturesClient(sandbox=False)
    # Testing ETH as our primary symbol
    symbol = "ETH/USDT:USDT"
    
    print(f"Testing {symbol} on {timeframe} timeframe:")
    
    # Need fresh fetch to get 1H/4H data
    df = client.fetch_ohlcv_df(symbol, timeframe=timeframe, limit=1000)
    df = calculate_indicators(df)
    atr = calculate_atr_pine(df['high'], df['low'], df['close'], 14)
    
    fee_rate, slippage = 0.0005, 0.0002
    tp_mult, sl_mult = 1.4, 0.4
    
    capital, trades, wins, position = 100, 0, 0, 0
    entry_price, tp_level, sl_level = 0.0, 0.0, 0.0
    
    for i in range(50, len(df)):
        close, high, low = df["close"].iloc[i], df["high"].iloc[i], df["low"].iloc[i]
        current_atr = atr.iloc[i]
        
        # Exit Logic
        if position != 0:
            if (position == 1 and (high >= tp_level or low <= sl_level)) or \
               (position == -1 and (low <= tp_level or high >= sl_level)):
                capital -= (capital * (fee_rate + slippage))
                if (position == 1 and high >= tp_level) or (position == -1 and low <= tp_level): wins += 1
                position = 0
        
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
    print(f"Trades: {trades}, WR: {wr:.2f}%, Return: {(capital-100):.2f}%")

run_tf_backtest("1h")
run_tf_backtest("4h")
