import os
import sys
import time
import signal
import logging
import argparse
from pathlib import Path
import yaml

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.binance_client import BinanceFuturesClient
from src.engine import SupertrendEngine

LOG_DIR = Path("/home/dy6z/workspace/binance-supertrend/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "runner.log")
    ]
)
log = logging.getLogger("binance-supertrend")

running = True

def handle_exit(signum, frame):
    global running
    log.info("Shutdown signal received. Exiting gracefully...")
    running = False

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

def load_config(config_path: str = "config/settings.yaml") -> dict:
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

def main():
    parser = argparse.ArgumentParser(description="Binance Futures SuperTrend Auto-Trader")
    parser.add_argument("--config", default="config/settings.yaml", help="Path to config file")
    parser.add_argument("--once", action="store_true", help="Run one evaluation cycle and exit")
    parser.add_argument("--live", action="store_true", help="Override config to run in LIVE mode")
    args = parser.parse_args()

    config = load_config(args.config)
    if args.live:
        config["exchange"]["sandbox"] = False

    is_sandbox = config.get("exchange", {}).get("sandbox", False)
    log.info(f"Starting Binance SuperTrend Bot. Mode: {'TESTNET' if is_sandbox else 'LIVE'}")

    client = BinanceFuturesClient(sandbox=is_sandbox)
    engine = SupertrendEngine(client, config)

    symbols = config.get("strategy", {}).get("symbols", ["BTC/USDT:USDT"])
    poll_interval = int(config.get("execution", {}).get("poll_interval_sec", 15))

    while running:
        for symbol in symbols:
            try:
                res = engine.evaluate_and_execute(symbol)
            except Exception as e:
                log.error(f"Error during execution for {symbol}: {e}", exc_info=True)

        if args.once:
            log.info("Single evaluation run completed.")
            break

        time.sleep(poll_interval)

if __name__ == "__main__":
    main()