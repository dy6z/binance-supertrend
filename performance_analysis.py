
import pandas as pd
import numpy as np
from src.binance_client import BinanceFuturesClient
from src.indicators import calculate_indicators

def run_analysis():
    client = BinanceFuturesClient(sandbox=False)
    symbols = ["BTC/USDT:USDT", "ETH/USDT:USDT", "SOL/USDT:USDT", "XRP/USDT:USDT", "ADA/USDT:USDT", "DOT/USDT:USDT", "LINK/USDT:USDT", "UNI/USDT:USDT", "AVAX/USDT:USDT", "ARB/USDT:USDT"]
    
    report = []
    
    for symbol in symbols:
        try:
            df = client.fetch_ohlcv_df(symbol, timeframe="15m", limit=3000)
            df = calculate_indicators(df)
            
            trades = 0
            capital = 100
            position = 0
            entry_price = 0
            
            # Logic: ST20 + EMA200
            for i in range(50, len(df)):
                close = df['close'].iloc[i]
                crossover_dn = (df['close'].iloc[i] > df['st_dn'].iloc[i]) and (df['close'].iloc[i-1] <= df['st_dn'].iloc[i-1])
                crossunder_up = (df['close'].iloc[i] < df['st_up'].iloc[i]) and (df['close'].iloc[i-1] >= df['st_up'].iloc[i-1])
                
                if crossover_dn and df['close'].iloc[i] > df['ema'].iloc[i] and position <= 0:
                    if position == -1: capital += (entry_price - close)
                    position = 1
                    entry_price = close
                    trades += 1
                elif crossunder_up and df['close'].iloc[i] < df['ema'].iloc[i] and position >= 0:
                    if position == 1: capital += (close - entry_price)
                    position = -1
                    entry_price = close
                    trades += 1
            
            report.append({
                "Symbol": symbol.split('/')[0],
                "Trades": trades,
                "Return": f"{(capital-100):.2f}%"
            })
        except:
            continue
    
    print(pd.DataFrame(report).to_string(index=False))

run_analysis()
