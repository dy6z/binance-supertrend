#!/usr/bin/env python3
import sys
import os
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.binance_client import BinanceFuturesClient

def main():
    client = BinanceFuturesClient(sandbox=False)
    print("\n=== BINANCE FUTURES STATUS ===")
    
    try:
        balance = client.exchange.fetch_balance()
        usdt_free = balance.get("USDT", {}).get("free", 0)
        usdt_total = balance.get("USDT", {}).get("total", 0)
        print(f"USDT Balance: {usdt_total:.2f} (Free: {usdt_free:.2f})")
    except Exception as e:
        print(f"Failed to fetch balance: {e}")

    positions = client.get_positions()
    if not positions:
        print("No active open positions.")
    else:
        print(f"\nActive Positions ({len(positions)}):")
        for p in positions:
            print(f"- {p['symbol']} | Side: {p['side']} | Contracts: {p['contracts']} | Entry: {p['entry_price']} | uPnL: {p['unrealized_pnl']:.4f} USDT | Lev: {p['leverage']}x ({p['margin_type']})")
    print("==============================\n")

if __name__ == "__main__":
    main()
