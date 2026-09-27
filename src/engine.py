import logging
import pandas as pd
import yaml
from pathlib import Path
from src.indicators import calculate_indicators

class SupertrendEngine:
    def __init__(self, client, config, notifier=None):
        self.client = client
        self.config = config
        self.notifier = notifier
        self.log = logging.getLogger("binance-supertrend")
        self.positions = {}
        
        # Load risk config from settings.yaml
        settings_path = Path(__file__).parent.parent / "config" / "settings.yaml"
        try:
            with open(settings_path, 'r') as f:
                settings = yaml.safe_load(f)
            self.risk_settings = settings.get('risk', {})
            # Global fallbacks
            self.tp_pct = self.risk_settings.get('take_profit_pct', 0.015)
            self.sl_pct = self.risk_settings.get('stop_loss_pct', 0.025)
            self.profit_lock_threshold = self.risk_settings.get('profit_lock_threshold', 0.01)
            # Per-symbol overrides (TP/SL/Lock/RWI)
            self.symbol_params = settings.get('strategy', {}).get('symbol_params', {})
            self.log.info(f"[Engine] Loaded global TP={self.tp_pct*100}%, SL={self.sl_pct*100}%, Lock={self.profit_lock_threshold*100}%")
            for sym, p in self.symbol_params.items():
                self.log.info(f"[Engine] Override {sym}: TP={p.get('take_profit_pct', self.tp_pct)*100}%, SL={p.get('stop_loss_pct', self.sl_pct)*100}%, Lock={p.get('profit_lock_threshold', self.profit_lock_threshold)*100}%, RWI={p.get('rwi_trigger', 1.0)}")
        except Exception as e:
            self.log.warning(f"Could not load settings.yaml: {e}. Using defaults.")
            self.tp_pct = 0.015
            self.sl_pct = 0.025
            self.profit_lock_threshold = 0.01
            self.symbol_params = {}

        # RWI triggers per symbol (default; overridden by symbol_params.rwi_trigger)
        self.rwi_triggers = {
            "ZEC": 1.0,
            "SNDK": 1.0,
            "SOL": 1.0,
            "1000PEPE": 1.2
        }

    def _params_for(self, sym_name):
        """Return (tp, sl, lock, rwi) for a symbol, falling back to global."""
        p = self.symbol_params.get(sym_name, {})
        return (
            p.get('take_profit_pct', self.tp_pct),
            p.get('stop_loss_pct', self.sl_pct),
            p.get('profit_lock_threshold', self.profit_lock_threshold),
            p.get('rwi_trigger', self.rwi_triggers.get(sym_name, 1.0)),
        )

    def _check_tp_sl(self, position_side, entry_price, current_price, tp_pct, sl_pct):
        """Check if TP/SL hit. Returns (should_close, reason)"""
        if position_side == "LONG":
            return_pct = (current_price - entry_price) / entry_price
            if return_pct >= tp_pct:
                return True, f"TP_HIT ({return_pct*100:.2f}%)"
            if return_pct <= -sl_pct:
                return True, f"SL_HIT ({return_pct*100:.2f}%)"
        elif position_side == "SHORT":
            return_pct = (entry_price - current_price) / entry_price
            if return_pct >= tp_pct:
                return True, f"TP_HIT ({return_pct*100:.2f}%)"
            if return_pct <= -sl_pct:
                return True, f"SL_HIT ({return_pct*100:.2f}%)"
        return False, None

    def evaluate_and_execute(self, symbol):
        sym_name = symbol.split("/")[0]
        tp_pct, sl_pct, lock_pct, rwi_trigger = self._params_for(sym_name)
        timeframe = "15m"
        
        try:
            df = self.client.fetch_ohlcv_df(symbol, timeframe=timeframe, limit=100)
            df = calculate_indicators(df, factor=3.0, atr_len=10, pivot_len=20, rwi_len=10)
            df = df.dropna()
            # Drop the still-forming candle: evaluate on the last CLOSED candle so
            # live signals match TradingView (flips on candle close) and backtests.
            df = df.iloc[:-1]
            if df.empty or len(df) < 2:
                return None
                
            last = df.iloc[-1]
            prev = df.iloc[-2]
            
            # Sync exchange position to internal state
            remote_pos = self.client.get_positions(symbol)
            if not remote_pos:
                if symbol in self.positions:
                    del self.positions[symbol]
                # Self-heal: exchange-side TP/SL exits leave the sibling algo
                # order behind (cleanup only runs on client-side close).
                self.client.cleanup_algo_orders(symbol)
                # No open position, check entry signals
                buy_ok = bool(last['crossover'] and (last['rwiVal'] >= rwi_trigger) and not last['nearRes'])
                sell_ok = bool(last['crossunder'] and (last['rwiVal'] >= rwi_trigger) and not last['nearSup'])
                if buy_ok:
                    return {"symbol": symbol, "side": "LONG", "action": "OPEN"}
                elif sell_ok:
                    return {"symbol": symbol, "side": "SHORT", "action": "OPEN"}
            else:
                pos = remote_pos[0]
                self.positions[symbol] = {
                    "side": pos['side'].upper(),
                    "entry_price": float(pos.get('entry_price', 0) or 0),
                    "contracts": float(pos.get('contracts', 0) or 0)
                }
                current_side = self.positions[symbol]["side"]
                entry_price = self.positions[symbol]["entry_price"]
                current_price = float(last['close'])
                
                # Pre-compute entry conditions for potential flip
                buy_ok = bool(last['crossover'] and (last['rwiVal'] >= rwi_trigger) and not last['nearRes'])
                sell_ok = bool(last['crossunder'] and (last['rwiVal'] >= rwi_trigger) and not last['nearSup'])
                
                # 1. TP/SL CHECK FIRST
                should_close, reason = self._check_tp_sl(current_side, entry_price, current_price, tp_pct, sl_pct)
                if should_close:
                    return {"symbol": symbol, "side": current_side, "action": "CLOSE", "reason": reason}
                
                # 2. SAFETY FLIP CHECK (only if profit > threshold)
                return_pct = (current_price - entry_price) / entry_price if current_side == "LONG" else (entry_price - current_price) / entry_price
                flip_ok = return_pct >= lock_pct
                
                if current_side == "LONG":
                    if sell_ok and flip_ok:
                        return {"symbol": symbol, "side": "SHORT", "action": "OPEN", "reason": "SAFETY_FLIP"}
                    elif last['crossunder']:
                        return {"symbol": symbol, "side": "LONG", "action": "CLOSE"}
                elif current_side == "SHORT":
                    if buy_ok and flip_ok:
                        return {"symbol": symbol, "side": "LONG", "action": "OPEN", "reason": "SAFETY_FLIP"}
                    elif last['crossover']:
                        return {"symbol": symbol, "side": "SHORT", "action": "CLOSE"}
                    
        except Exception as e:
            self.log.error(f"Error evaluating {symbol}: {e}")
        return None