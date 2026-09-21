#!/usr/bin/env python3.12
"""
Execute RSI + EMA + Stochastic strategy.

Entry: RSI + Stoch double oversold/overbought + EMA trend
Exit: RSI flip or SL 2xATR
"""
import json
import sys
import argparse
from pathlib import Path
from datetime import datetime, timezone

from ctrader_open_api import Client, EndPoints, Protobuf, TcpProtocol
from ctrader_open_api.messages.OpenApiMessages_pb2 import *
from ctrader_open_api.messages.OpenApiModelMessages_pb2 import (
    ProtoOAOrderType, ProtoOATradeSide
)
from twisted.internet import reactor, defer

# Constants
MARKET = ProtoOAOrderType.MARKET
BUY = ProtoOATradeSide.BUY
SELL = ProtoOATradeSide.SELL
ORDER_ACCEPTED = 2

sys.path.insert(0, str(Path(__file__).parent))
from config import (
    ACCOUNT_ID, SYMBOL_MAP, FIXED_LOT, PIP_SIZES,
    RSI_PERIOD, RSI_OVERSOLD, RSI_OVERBOUGHT, ATR_PERIOD
)

# Load credentials
env = {}
for line in Path.home().joinpath(".agent/credentials/ctrader.env").read_text().splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    env[k.strip()] = v.strip().strip('"').strip("'")

# State
state_path = Path(__file__).parent.parent / "output" / "trading_state.json"
signal_path = Path(__file__).parent.parent / "output" / "signal_latest.json"

client = Client(EndPoints.PROTOBUF_DEMO_HOST, EndPoints.PROTOBUF_PORT, TcpProtocol)

# Global state
DRY_RUN = False
symbols_map = {}
symbol_ids = {}
positions_from_broker = {}
balance = 0.0
current_indicators = {}  # {pair: {"rsi": ..., "stoch": ...}}


def load_state():
    if state_path.exists():
        return json.loads(state_path.read_text())
    return {"positions": {}, "balance": 0.0, "last_run": None, "trades": []}


def save_state(state):
    state_path.parent.mkdir(exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2, default=str))


def load_signal():
    if not signal_path.exists():
        return None
    return json.loads(signal_path.read_text())


def load_current_indicators():
    """Load latest RSI/Stoch values from candles for exit logic."""
    import pickle
    import pandas as pd
    import numpy as np
    
    pkl_path = Path(__file__).parent.parent / "data" / "candles.pkl"
    candles = pickle.load(open(pkl_path, "rb"))
    
    indicators = {}
    for pair, bars in candles.items():
        df = pd.DataFrame(bars)
        if len(df) < RSI_PERIOD + 10:
            continue
        
        # RSI
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0).rolling(RSI_PERIOD).mean()
        loss = -delta.where(delta < 0, 0).rolling(RSI_PERIOD).mean()
        rsi = 100 - (100 / (1 + gain / loss))
        
        # Stochastic
        low_min = df["low"].rolling(14).min()
        high_max = df["high"].rolling(14).max()
        stoch = 100 * (df["close"] - low_min) / (high_max - low_min)
        
        curr_rsi = rsi.iloc[-1]
        curr_stoch = stoch.iloc[-1]
        
        if not pd.isna(curr_rsi) and not pd.isna(curr_stoch):
            indicators[pair] = {"rsi": float(curr_rsi), "stoch": float(curr_stoch)}
    
    return indicators


def stop(msg=None):
    if msg:
        print(msg)
    if reactor.running:
        reactor.stop()


def fresh_id():
    import uuid
    return str(uuid.uuid4())[:8]


@defer.inlineCallbacks
def execute_flow():
    """Main async execution flow."""
    global balance, positions_from_broker, current_indicators
    
    # Auth
    r = ProtoOAApplicationAuthReq()
    r.clientId = env["CTRADER_CLIENT_ID"]
    r.clientSecret = env["CTRADER_CLIENT_SECRET"]
    yield client.send(r, clientMsgId=fresh_id(), responseTimeoutInSeconds=25)
    
    r = ProtoOAAccountAuthReq()
    r.ctidTraderAccountId = ACCOUNT_ID
    r.accessToken = env["CTRADER_ACCESS_TOKEN"]
    yield client.send(r, clientMsgId=fresh_id(), responseTimeoutInSeconds=25)
    
    # Fetch symbols
    r = ProtoOASymbolsListReq()
    r.ctidTraderAccountId = ACCOUNT_ID
    msg = yield client.send(r, clientMsgId=fresh_id(), responseTimeoutInSeconds=25)
    res = Protobuf.extract(msg)
    for sym in res.symbol:
        name = sym.symbolName.replace("/", "_")
        symbols_map[sym.symbolId] = name
        symbol_ids[name] = sym.symbolId
    
    print(f"Loaded {len(symbols_map)} symbols")
    
    # Fetch positions
    r = ProtoOAReconcileReq()
    r.ctidTraderAccountId = ACCOUNT_ID
    msg = yield client.send(r, clientMsgId=fresh_id(), responseTimeoutInSeconds=25)
    res = Protobuf.extract(msg)
    
    balance = float(res.balance) / (10 ** res.moneyDigits) if hasattr(res, "balance") else 0.0
    
    for pos in res.position:
        sym_name = symbols_map.get(pos.tradeData.symbolId, f"sym{pos.tradeData.symbolId}")
        side = "long" if pos.tradeData.tradeSide == BUY else "short"
        positions_from_broker[sym_name] = {
            "positionId": pos.positionId,
            "side": side,
            "volume": pos.tradeData.volume,
            "entry": pos.price,
            "sl": pos.stopLoss if pos.hasStopLoss else None,
        }
    
    print(f"Balance: ${balance:.2f}")
    print(f"Current positions: {len(positions_from_broker)}")
    
    # Load current indicators for exit logic
    current_indicators = load_current_indicators()
    
    # Execute strategy
    yield execute_strategy()
    
    stop()


@defer.inlineCallbacks
def execute_strategy():
    """Main execution logic."""
    signal = load_signal()
    state = load_state()
    
    if not signal:
        print("No signal file found")
        return
    
    entries = signal.get("entries", [])
    
    print(f"\n[Strategy Execution]")
    print(f"  Entries: {len(entries)}")
    print(f"  Open positions: {len(positions_from_broker)}")
    
    if DRY_RUN:
        print("\n🔵 DRY-RUN MODE — no real orders")
    
    # Check exits (RSI flip)
    for pair, pos in list(positions_from_broker.items()):
        if pair not in current_indicators:
            continue
        
        curr_rsi = current_indicators[pair]["rsi"]
        close_reason = None
        
        # Long exit: RSI > overbought
        if pos["side"] == "long" and curr_rsi > RSI_OVERBOUGHT:
            close_reason = "rsi_overbought"
        # Short exit: RSI < oversold
        elif pos["side"] == "short" and curr_rsi < RSI_OVERSOLD:
            close_reason = "rsi_oversold"
        
        if close_reason:
            print(f"  EXIT {pair} ({close_reason}, RSI={curr_rsi:.1f})")
            
            if not DRY_RUN:
                req = ProtoOAClosePositionReq()
                req.ctidTraderAccountId = ACCOUNT_ID
                req.positionId = pos["positionId"]
                req.volume = pos["volume"]
                try:
                    yield client.send(req, clientMsgId=fresh_id(), responseTimeoutInSeconds=30)
                    state["trades"].append({
                        "action": "close",
                        "symbol": pair,
                        "reason": close_reason,
                        "time": datetime.now(timezone.utc).isoformat(),
                    })
                    del positions_from_broker[pair]
                except Exception as e:
                    print(f"    FAILED: {e}")
    
    # Handle entries
    for entry_signal in entries:
        pair = entry_signal["symbol"]
        if pair in positions_from_broker:
            continue
        
        side = entry_signal["side"]
        sl_distance = entry_signal["sl_distance"]
        close_price = entry_signal["close"]
        
        if side == "long":
            sl_price = close_price - sl_distance
            trade_side = BUY
        else:
            sl_price = close_price + sl_distance
            trade_side = SELL
        
        ct_name = SYMBOL_MAP.get(pair)
        if not ct_name or ct_name not in symbol_ids:
            print(f"  SKIP {pair} — not found")
            continue
        
        sym_id = symbol_ids[ct_name]
        
        print(f"  ENTRY {side.upper()} {pair} (RSI={entry_signal['rsi']:.1f}, Stoch={entry_signal['stoch']:.1f})")
        
        if not DRY_RUN:
            req = ProtoOANewOrderReq()
            req.ctidTraderAccountId = ACCOUNT_ID
            req.symbolId = sym_id
            req.orderType = MARKET
            req.tradeSide = trade_side
            req.volume = FIXED_LOT
            req.stopLoss = int(sl_price * 100000)
            req.relativeStopLoss = False
            
            try:
                msg = yield client.send(req, clientMsgId=fresh_id(), responseTimeoutInSeconds=30)
                res = Protobuf.extract(msg)
                
                if res.executionType == ORDER_ACCEPTED and hasattr(res, "position"):
                    print(f"    ✅ Opened position ID {res.position.positionId}")
                    state["trades"].append({
                        "action": "open",
                        "symbol": pair,
                        "side": side,
                        "entry": close_price,
                        "sl": sl_price,
                        "time": datetime.now(timezone.utc).isoformat(),
                    })
                else:
                    print(f"    ⚠️ Not filled: executionType={res.executionType}")
            except Exception as e:
                print(f"    FAILED: {e}")
    
    # Update state
    state["last_run"] = datetime.now(timezone.utc).isoformat()
    state["balance"] = balance
    state["positions"] = {k: v for k, v in positions_from_broker.items()}
    save_state(state)
    
    print("\nExecution complete")


def connected(_):
    execute_flow().addErrback(lambda f: stop(f"ERROR: {f}"))


def main():
    global DRY_RUN
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Print without executing")
    args = parser.parse_args()
    
    DRY_RUN = args.dry_run
    
    client.setConnectedCallback(connected)
    client.setDisconnectedCallback(lambda *a: None)
    client.startService()
    reactor.run()


if __name__ == "__main__":
    main()
