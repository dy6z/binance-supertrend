import logging
import time
import yaml
from pathlib import Path
from src.binance_client import BinanceFuturesClient
from src.engine import SupertrendEngine

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
log = logging.getLogger("binance-supertrend")

def load_settings():
    settings_path = Path(__file__).parent.parent / "config" / "settings.yaml"
    with open(settings_path) as f:
        return yaml.safe_load(f)

def run():
    client = BinanceFuturesClient()
    settings = load_settings()
    strategy = settings.get('strategy', {})
    sp = strategy.get('symbol_params', {})

    # Symbols from settings.yaml strategy.symbols (single source of truth).
    # AKE removed 2026-09-26 (negative PF 60d). INJ added 2026-09-28 (PF 1.17 grid).
    symbols = strategy.get('symbols', ["BTC/USDT:USDT", "SOL/USDT:USDT", "ZEC/USDT:USDT",
                                      "SNDK/USDT:USDT", "1000PEPE/USDT:USDT"])
    # Per-symbol leverage override (BTC uses 5x per settings.yaml btc_leverage)
    lev_override = {"BTC": settings.get('risk', {}).get('btc_leverage', 5)}
    log.info(f"Starting Binance SuperTrend Bot | Symbols: {symbols}")

    engine = SupertrendEngine(client, settings)

    while True:
        try:
            for symbol in symbols:
                sym_name = symbol.split("/")[0]
                params = sp.get(sym_name, {})
                action = engine.evaluate_and_execute(symbol)
                if action:
                    log.info(f"Action: {action}")
                    try:
                        if action['action'] == 'OPEN':
                            side = "BUY" if action['side'] == "LONG" else "SELL"
                            res = client.open_position(
                                symbol=action['symbol'],
                                side=side,
                                margin_usdt=1.0,
                                leverage=lev_override.get(sym_name, 10),
                                tp_pct=params.get('take_profit_pct', 0.015),
                                sl_pct=params.get('stop_loss_pct', 0.025)
                            )
                            log.info(f"Result: {res}")
                        elif action['action'] == 'CLOSE':
                            res = client.close_position(action['symbol'])
                            log.info(f"Result: {res}")
                    except Exception as e:
                        log.error(f"Execution failed: {e}")
            time.sleep(10)
        except Exception as e:
            log.error(f"Error, retry in 30s... {e}")
            time.sleep(30)

if __name__ == "__main__":
    run()