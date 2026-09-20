import os
import logging
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd
import ccxt

log = logging.getLogger("binance-supertrend")

# Path to credential file
CRED_PATH = Path.home() / ".agent" / "credentials" / "binance.env"
load_dotenv(CRED_PATH)

class BinanceFuturesClient:
    def __init__(self, sandbox=False):
        api_key = os.getenv("BINANCE_API_KEY") or os.getenv("API_KEY", "")
        api_secret = os.getenv("BINANCE_API_SECRET") or os.getenv("API_SECRET", "")
        
        if not api_key or not api_secret:
            log.warning("No Binance API credentials found in environment or credential file.")

        self.exchange = ccxt.binance({
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
            "options": {
                "defaultType": "future",
                "adjustForTimeDifference": True,
            }
        })
        
        if sandbox:
            self.exchange.set_sandbox_mode(True)
            log.info("Binance client initialized in TESTNET / SANDBOX mode.")
        else:
            log.info("Binance client initialized in LIVE mode.")

        # Preload markets to have accurate symbol precision and limits
        try:
            self.markets = self.exchange.load_markets()
        except Exception as e:
            log.error(f"Failed to load markets: {e}")
            self.markets = {}

    def fetch_ohlcv_df(self, symbol: str, timeframe: str = "5m", limit: int = 150) -> pd.DataFrame:
        """Fetch OHLCV candlestick data and return as clean DataFrame."""
        raw = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        df = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms")
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = df[col].astype(float)
        return df

    def get_positions(self, symbol: str = None) -> list:
        """Get open futures positions."""
        try:
            positions = self.exchange.fetch_positions(symbols=[symbol] if symbol else None)
            active = []
            for p in positions:
                contracts = float(p.get("contracts", 0) or 0)
                if abs(contracts) > 0:
                    active.append({
                        "symbol": p["symbol"],
                        "side": p["side"].upper(), # 'long' or 'short'
                        "contracts": contracts,
                        "entry_price": float(p.get("entryPrice", 0) or 0),
                        "unrealized_pnl": float(p.get("unrealizedPnl", 0) or 0),
                        "leverage": int(p.get("leverage", 10) or 10),
                        "margin_type": p.get("marginType", "isolated").lower(),
                    })
            return active
        except Exception as e:
            log.error(f"Error fetching positions: {e}")
            return []

    def set_leverage_and_margin_mode(self, symbol: str, leverage: int = 10, margin_mode: str = "ISOLATED"):
        """Configure margin mode and leverage for symbol."""
        try:
            self.exchange.set_margin_mode(margin_mode.upper(), symbol)
        except Exception as e:
            # Ignore if already set to that mode
            if "No need to change" not in str(e):
                log.debug(f"Margin mode note for {symbol}: {e}")

        try:
            self.exchange.set_leverage(leverage, symbol)
        except Exception as e:
            log.debug(f"Leverage note for {symbol}: {e}")

    def close_position(self, symbol: str) -> bool:
        """Close any existing open position for the symbol via market reduceOnly order."""
        positions = self.get_positions(symbol)
        if not positions:
            return True

        for pos in positions:
            side = "sell" if pos["side"] == "LONG" else "buy"
            amount = abs(pos["contracts"])
            log.info(f"Closing position on {symbol}: {pos['side']} {amount} contracts")
            try:
                self.exchange.create_order(
                    symbol=symbol,
                    type="market",
                    side=side,
                    amount=amount,
                    params={"reduceOnly": True}
                )
            except Exception as e:
                log.error(f"Failed to close position on {symbol}: {e}")
                return False
        return True

    def calculate_quantity(self, symbol: str, margin_usdt: float, leverage: int, current_price: float) -> float:
        """Calculate order quantity based on fixed USD margin and leverage, adjusted for exchange lot step."""
        notional = margin_usdt * leverage
        raw_qty = notional / current_price
        formatted_qty_str = self.exchange.amount_to_precision(symbol, raw_qty)
        qty = float(formatted_qty_str)
        
        # Check minimum limits
        market = self.markets.get(symbol)
        if market and "limits" in market:
            min_amount = market["limits"]["amount"]["min"]
            min_cost = market["limits"]["cost"]["min"]
            if min_amount and qty < min_amount:
                qty = float(self.exchange.amount_to_precision(symbol, min_amount))
            if min_cost and (qty * current_price) < min_cost:
                qty = float(self.exchange.amount_to_precision(symbol, (min_cost * 1.05) / current_price))
        return qty

    def fetch_balance(self) -> float:
        """Fetch total USDT wallet balance on futures account."""
        try:
            balance = self.exchange.fetch_balance()
            usdt_total = float(balance.get("USDT", {}).get("total", 0) or 0)
            return usdt_total
        except Exception as e:
            log.error(f"Failed to fetch balance: {e}")
            return 0.0

    def fetch_daily_realized_pnl(self) -> float:
        """Fetch today's total realized PnL from Binance income history (REALIZED_PNL type)."""
        import datetime
        try:
            # Start of today UTC
            now = datetime.datetime.utcnow()
            start_of_day = datetime.datetime(now.year, now.month, now.day)
            since_ms = int(start_of_day.timestamp() * 1000)

            # Use Binance fapiPrivateGetIncome endpoint
            params = {
                "incomeType": "REALIZED_PNL",
                "startTime": since_ms,
                "limit": 1000,
            }
            incomes = self.exchange.fapiPrivateGetIncome(params)
            total_pnl = sum(float(i.get("income", 0)) for i in incomes)
            return total_pnl
        except Exception as e:
            log.error(f"Failed to fetch daily realized PnL: {e}")
            return 0.0

    def open_position(self, symbol: str, side: str, margin_usdt: float = 1.0, leverage: int = 10,
                      tp_pct: float = 0.015, sl_pct: float = 0.010, use_tp_sl: bool = True) -> dict:
        """Open a new futures position with TP and SL orders."""
        self.set_leverage_and_margin_mode(symbol, leverage, "ISOLATED")

        ticker = self.exchange.fetch_ticker(symbol)
        current_price = float(ticker["last"])

        qty = self.calculate_quantity(symbol, margin_usdt, leverage, current_price)
        if qty <= 0:
            log.error(f"Calculated invalid quantity {qty} for {symbol}")
            return {"status": "error", "message": "Invalid quantity"}

        order_side = "buy" if side.upper() == "BUY" else "sell"
        log.info(f"Placing {order_side.upper()} order for {qty} {symbol} @ ~{current_price}")

        try:
            main_order = self.exchange.create_order(
                symbol=symbol,
                type="market",
                side=order_side,
                amount=qty
            )
            log.info(f"Main order filled: {main_order.get('id')}")

            # Place TP and SL if enabled
            if use_tp_sl and (tp_pct > 0 or sl_pct > 0):
                close_side = "sell" if order_side == "buy" else "buy"
                
                # Take Profit
                if tp_pct > 0:
                    tp_price = current_price * (1 + tp_pct) if order_side == "buy" else current_price * (1 - tp_pct)
                    tp_price_str = self.exchange.price_to_precision(symbol, tp_price)
                    try:
                        self.exchange.create_order(
                            symbol=symbol,
                            type="TAKE_PROFIT_MARKET",
                            side=close_side,
                            amount=qty,
                            params={"stopPrice": float(tp_price_str), "reduceOnly": True}
                        )
                        log.info(f"TP order placed @ {tp_price_str}")
                    except Exception as e:
                        log.warning(f"Failed to place TP order: {e}")

                # Stop Loss
                if sl_pct > 0:
                    sl_price = current_price * (1 - sl_pct) if order_side == "buy" else current_price * (1 + sl_pct)
                    sl_price_str = self.exchange.price_to_precision(symbol, sl_price)
                    try:
                        self.exchange.create_order(
                            symbol=symbol,
                            type="STOP_MARKET",
                            side=close_side,
                            amount=qty,
                            params={"stopPrice": float(sl_price_str), "reduceOnly": True}
                        )
                        log.info(f"SL order placed @ {sl_price_str}")
                    except Exception as e:
                        log.warning(f"Failed to place SL order: {e}")

            return {"status": "success", "order": main_order}
        except Exception as e:
            log.error(f"Failed to execute open_position for {symbol}: {e}")
            return {"status": "error", "message": str(e)}
