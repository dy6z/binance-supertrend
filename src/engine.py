import logging
from datetime import datetime
import pandas as pd
from src.indicators import calculate_indicators

class SupertrendEngine:
    def __init__(self, client, config, notifier=None):
        self.client = client
        self.config = config
        self.notifier = notifier
        self.log = logging.getLogger("binance-supertrend")
        self.positions = {}
        # Define symbol-specific RWI triggers
        self.rwi_triggers = {
            "ETH": 1.0,
            "ZEC": 1.3,
            "SNDK": 1.3,
            "SOL": 1.3
        }

    def is_in_window(self):
        now = datetime.now().time()
        start = datetime.strptime("09:00", "%H:%M").time()
        end = datetime.strptime("13:30", "%H:%M").time()
        return start <= now <= end

    def evaluate_and_execute(self, symbol):
        # Extract symbol name for trigger lookup (e.g., "ETH/USDT:USDT" -> "ETH")
        sym_name = symbol.split("/")[0]
        rwi_trigger = self.rwi_triggers.get(sym_name, 1.0)
        
        timeframe = "15m"
        try:
            df = self.client.fetch_ohlcv_df(symbol, timeframe=timeframe, limit=100)
            df = calculate_indicators(df)
            
            # Pivot Filter logic (20-bar window)
            df['pivot_high'] = df['high'].rolling(window=20, center=True).max()
            df['pivot_low'] = df['low'].rolling(window=20, center=True).min()
            
            last = df.iloc[-1]
            prev = df.iloc[-2]
            
            # S&R Pivot Check
            near_resistance = last['close'] > (last['pivot_high'] * 0.995)
            near_support = last['close'] < (last['pivot_low'] * 1.005)
            
            crossover_dn = (last['close'] > last['st_dn']) and (prev['close'] <= prev['st_dn'])
            crossunder_up = (last['close'] < last['st_up']) and (prev['close'] >= prev['st_up'])
            
            # Flip Logic with S&R Filter and Dynamic RWI
            if symbol not in self.positions and self.is_in_window():
                if crossover_dn and last['close'] > last['ema'] and last['rwi_high'] >= rwi_trigger and not near_resistance:
                    self.positions[symbol] = {"side": "LONG"}
                    return {"symbol": symbol, "side": "LONG", "action": "OPEN"}
                elif crossunder_up and last['close'] < last['ema'] and last['rwi_low'] >= rwi_trigger and not near_support:
                    self.positions[symbol] = {"side": "SHORT"}
                    return {"symbol": symbol, "side": "SHORT", "action": "OPEN"}
            elif symbol in self.positions:
                if self.positions[symbol]["side"] == "LONG" and crossunder_up:
                    del self.positions[symbol]
                    return {"symbol": symbol, "side": "LONG", "action": "CLOSE"}
                elif self.positions[symbol]["side"] == "SHORT" and crossover_dn:
                    del self.positions[symbol]
                    return {"symbol": symbol, "side": "SHORT", "action": "CLOSE"}
        except Exception as e:
            self.log.error(f"Error evaluating {symbol}: {e}")
        return None
