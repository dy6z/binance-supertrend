import os
import logging
import traceback
from pathlib import Path
from decimal import Decimal, ROUND_DOWN
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

        try:
            self.markets = self.exchange.load_markets()
        except Exception as e:
            log.error(f"Failed to load markets: {e}")
            self.markets = {}

    def fetch_ohlcv_df(self, symbol: str, timeframe: str = "5m", limit: int = 150) -> pd.DataFrame:
        raw = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        df = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms")
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = df[col].astype(float)
        return df

    def get_positions(self, symbol: str = None) -> list:
        try:
            positions = self.exchange.fetch_positions(symbols=[symbol] if symbol else None)
            active = []
            for p in positions:
                contracts = float(p.get("contracts", 0) or 0)
                if abs(contracts) > 0:
                    active.append({
                        "symbol": p["symbol"],
                        "side": p["side"].upper(),
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
        try:
            self.exchange.set_margin_mode(margin_mode.upper(), symbol)
        except Exception as e:
            if "No need to change" not in str(e):
                log.debug(f"Margin mode note for {symbol}: {e}")

        try:
            self.exchange.set_leverage(leverage, symbol)
        except Exception as e:
            log.debug(f"Leverage note for {symbol}: {e}")

    def close_position(self, symbol: str) -> bool:
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
                log.error(traceback.format_exc())
                return False
        # Clean up any orphaned algo orders for this symbol
        self.cleanup_algo_orders(symbol)
        return True

    def calculate_quantity(self, symbol: str, margin_usdt: float, leverage: int, current_price: float) -> float:
        market = self.markets.get(symbol) or {}
        base_notional = margin_usdt * leverage

        min_cost = float(market.get("limits", {}).get("cost", {}).get("min") or 5.0)
        min_amount = float(market.get("limits", {}).get("amount", {}).get("min") or 0.0)
        step_size = float(market.get("precision", {}).get("amount") or min_amount or 1.0)

        target_notional = max(base_notional, min_cost)

        raw_qty = target_notional / current_price
        if raw_qty < min_amount:
            raw_qty = min_amount

        step_dec = Decimal(str(step_size))
        raw_dec = Decimal(str(raw_qty))
        quantized = (raw_dec / step_dec).to_integral_value(rounding=ROUND_DOWN) * step_dec

        if float(quantized) < min_amount or (float(quantized) * current_price) < min_cost:
            quantized += step_dec

        try:
            formatted_qty = float(self.exchange.amount_to_precision(symbol, float(quantized)))
        except Exception:
            formatted_qty = float(quantized)

        return formatted_qty

    def fetch_balance(self) -> float:
        try:
            balance = self.exchange.fetch_balance()
            usdt_total = float(balance.get("USDT", {}).get("total", 0) or 0)
            return usdt_total
        except Exception as e:
            log.error(f"Failed to fetch balance: {e}")
            return 0.0

    def open_position(self, symbol: str, side: str, margin_usdt: float = 1.0, leverage: int = 10, tp_pct: float = 0.12, sl_pct: float = 0.08) -> dict:
        self.set_leverage_and_margin_mode(symbol, leverage, "ISOLATED")

        ticker = self.exchange.fetch_ticker(symbol)
        current_price = float(ticker["last"])

        qty = self.calculate_quantity(symbol, margin_usdt, leverage, current_price)
        if qty <= 0:
            log.error(f"Calculated invalid quantity {qty} for {symbol}")
            return {"status": "error", "message": "Invalid quantity"}

        order_side = "buy" if side.upper() == "BUY" else "sell"
        log.info(f"Placing {order_side.upper()} order for {qty} {symbol} @ ~{current_price} (Notional: ~{qty * current_price:.2f} USDT)")

        try:
            main_order = self.exchange.create_order(
                symbol=symbol,
                type="market",
                side=order_side,
                amount=qty
            )
            log.info(f"Main order filled: {main_order.get('id')}")

            # Auto TP/SL using Algo API (values come from runner / settings symbol_params)
            close_side = "sell" if order_side == "buy" else "buy"
            if order_side == "buy":
                tp_price = current_price * (1 + tp_pct)
                sl_price = current_price * (1 - sl_pct)
            else:
                tp_price = current_price * (1 - tp_pct)
                sl_price = current_price * (1 + sl_pct)
            log.info(f"TP level: {tp_price:.4f} (+/-{tp_pct*100}%), SL level: {sl_price:.4f} (+/-{sl_pct*100}%)")
            
            for price, algo_type in [(tp_price, "TAKE_PROFIT_MARKET"), (sl_price, "STOP_MARKET")]:
                try:
                    self.exchange.create_order( # Using algo API parameters
                        symbol=symbol,
                        type=algo_type,
                        side=close_side,
                        amount=qty,
                        params={
                            "stopPrice": float(self.exchange.price_to_precision(symbol, price)),
                            "reduceOnly": True,
                            "workingType": "MARK_PRICE",
                            "algoType": algo_type
                        }
                    )
                    log.info(f"{algo_type} placed at {price:.4f}")
                except Exception as e:
                    log.error(f"Failed to place {algo_type} for {symbol} at {price:.4f}: {e}")
                    log.error(traceback.format_exc())

            return {"status": "success", "order": main_order}
        except Exception as e:
            log.error(f"Failed to execute open_position for {symbol}: {e}")
            log.error(traceback.format_exc())
            return {"status": "error", "message": str(e)}

    def cleanup_algo_orders(self, symbol: str) -> None:
        """Cancel open algo orders (TP/SL) for this symbol ONLY.

        BUGFIX 2026-09-28: native algo API needs the market id (ZECUSDT), not the
        CCXT unified symbol (ZEC/USDT:USDT). Passing the wrong format makes the
        filter ignored, the API returns the WHOLE account's open algos, and this
        method was wiping other symbols' TP/SL (observed: ZEC's stop deleted
        under a 'for SOL' log, INJ's stop deleted under a 'for BTC' log).
        Now we convert the symbol and delete only orders belonging to it.
        """
        try:
            native_sym = self.exchange.market_id(symbol)
            if not native_sym:
                log.warning(f"Cannot resolve native symbol id for {symbol}, skipping cleanup")
                return
            algo_orders = self.exchange.fapiPrivateGetOpenAlgoOrders({"symbol": native_sym})
            if isinstance(algo_orders, dict):
                algo_orders = algo_orders.get("orders", [])

            for ao in algo_orders:
                if ao.get("symbol") and ao["symbol"] != native_sym:
                    continue  # never touch another symbol's orders
                try:
                    self.exchange.fapiPrivateDeleteAlgoOrder({
                        "symbol": native_sym,
                        "algoId": ao["algoId"]
                    })
                    log.info(f"Cleaned orphan algo order {ao['algoId']} for {symbol}")
                except Exception as e:
                    log.warning(f"Failed to clean algo {ao.get('algoId')}: {e}")
        except Exception as e:
            log.warning(f"Failed to fetch/clean algo orders for {symbol}: {e}")

    def close_all_positions(self) -> dict:
        positions = self.get_positions()
        results = {"closed": [], "errors": []}
        if not positions:
            return results
        for pos in positions:
            if self.close_position(pos["symbol"]):
                results["closed"].append(pos["symbol"])
            else:
                results["errors"].append(pos["symbol"])
        return results
