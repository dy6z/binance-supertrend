import pandas as pd
import numpy as np
import itertools
from pathlib import Path
from src.indicators import calculate_indicators

# Load engine logic inline (avoid module import side-effects)
def calculate_indicators(df, factor=3.0, atr_len=10, pivot_len=20, rwi_len=10):
    import pandas as pd, numpy as np
    df = df.copy()
    from src.indicators import calculate_supertrend_pine
    st_df = calculate_supertrend_pine(df, factor=factor, length=atr_len)
    df = pd.concat([df, st_df], axis=1)
    df['pHigh'] = df['high'].rolling(pivot_len).max()
    df['pLow'] = df['low'].rolling(pivot_len).min()
    df['rwiVal'] = (df['high'].rolling(rwi_len).max() - df['low'].rolling(rwi_len).min()) / (df['atr'] * np.sqrt(rwi_len))
    df['nearRes'] = df['close'] > (df['pHigh'] * 0.999)
    df['nearSup'] = df['close'] < (df['pLow'] * 1.001)
    df['crossover'] = (df['direction'].shift(1) == 1) & (df['direction'] == -1)
    df['crossunder'] = (df['direction'].shift(1) == -1) & (df['direction'] == 1)
    return df.dropna()

def backtest_hybrid(df, tp_pct, sl_pct, lock_pct, rwi_trigger, factor=3.0, atr_len=10, pivot_len=20, rwi_len=10):
    """Simulate SuperRWI + hybrid exit. Returns metrics dict."""
    position = None  # dict: side, entry, contracts
    trades = []
    equity = 1.0
    wins = 0
    losses = 0
    gross_profit = 0.0
    gross_loss = 0.0
    
    last = df.iloc[-1]
    for i in range(1, len(df)):
        row = df.iloc[i]
        current_price = float(row['close'])
        
        if position:
            side = position['side']
            entry = position['entry']
            if side == 'LONG':
                ret = (current_price - entry) / entry
            else:
                ret = (entry - current_price) / entry
            
            # TP/SL check first
            if side == 'LONG' and (ret >= tp_pct or ret <= -sl_pct):
                pnl = ret
            elif side == 'SHORT' and (ret >= tp_pct or ret <= -sl_pct):
                pnl = ret
            else:
                pnl = 0.0
            
            # Safety flip check
            buy_ok = bool(row['crossover'] and (row['rwiVal'] >= rwi_trigger) and not row['nearRes'])
            sell_ok = bool(row['crossunder'] and (row['rwiVal'] >= rwi_trigger) and not row['nearSup'])
            
            flipped = False
            if side == 'LONG':
                if sell_ok and ret >= lock_pct:
                    # Close long, open short
                    pnl = ret
                    position = {'side': 'SHORT', 'entry': current_price}
                    flipped = True
                elif row['crossunder']:
                    pnl = ret
                    position = None
            elif side == 'SHORT':
                if buy_ok and ret >= lock_pct:
                    pnl = ret
                    position = {'side': 'LONG', 'entry': current_price}
                    flipped = True
                elif row['crossover']:
                    pnl = ret
                    position = None
            
            if not flipped:
                if pnl != 0.0:
                    if pnl > 0: wins += 1
                    else: losses += 1
                    gross_profit += max(pnl, 0)
                    gross_loss += min(pnl, 0)
                    equity *= (1 + pnl)
                position = None
            
        # Entry signal when no position
        if position is None:
            buy_ok = bool(row['crossover'] and (row['rwiVal'] >= rwi_trigger) and not row['nearRes'])
            sell_ok = bool(row['crossunder'] and (row['rwiVal'] >= rwi_trigger) and not row['nearSup'])
            if buy_ok:
                position = {'side': 'LONG', 'entry': current_price}
            elif sell_ok:
                position = {'side': 'SHORT', 'entry': current_price}
    
    total_trades = wins + losses
    pf = gross_profit / abs(gross_loss) if gross_loss != 0 else float('inf')
    wr = (wins / total_trades * 100) if total_trades > 0 else 0
    return {'trades': total_trades, 'win_rate': round(wr, 2), 'profit_factor': round(pf, 3), 'final_equity': round(equity, 4)}

SYMBOLS = {
    'ZEC': '/home/dy6z/workspace/binance-supertrend/data_snapshot/data_ZEC.csv',
    'SNDK': '/home/dy6z/workspace/binance-supertrend/data_snapshot/data_SNDK.csv',
    '1000PEPE': '/home/dy6z/workspace/binance-supertrend/data_snapshot/data_1000PEPE_10k.csv',
    'AKE': '/home/dy6z/workspace/binance-supertrend/data_snapshot/data_AKEUSDT.csv',
}

TP_GRID = [0.015, 0.02, 0.03]
SL_GRID = [0.025, 0.03, 0.04]
LOCK_GRID = [0.005, 0.01, 0.015, 0.02]
RWI_GRID = [0.8, 1.0, 1.2]

combos = list(itertools.product(TP_GRID, SL_GRID, LOCK_GRID, RWI_GRID))
print(f"Total combos to test: {len(combos)}")

results = []
for sym, path in SYMBOLS.items():
    df_raw = pd.read_csv(path)
    df_raw = df_raw.drop(columns=[c for c in df_raw.columns if c not in ['open','high','low','close','volume']], errors='ignore')
    df_raw['timestamp'] = pd.to_datetime(df_raw.get('timestamp', pd.to_datetime(df_raw.index)))
    if 'timestamp' not in df_raw.columns:
        df_raw['timestamp'] = pd.to_datetime(df_raw.index)
    df_raw = df_raw.set_index('timestamp') if 'timestamp' in df_raw.columns else df_raw
    df = calculate_indicators(df_raw, factor=3.0, atr_len=10, pivot_len=20, rwi_len=10)
    print(f"Loaded {sym}: {len(df)} candles")
    
    for tp, sl, lock, rwi in combos:
        res = backtest_hybrid(df, tp, sl, lock, rwi)
        res.update({'symbol': sym, 'tp_pct': tp, 'sl_pct': sl, 'lock_pct': lock, 'rwi': rwi})
        results.append(res)

df_res = pd.DataFrame(results)
# Rank by profit_factor, prefer more trades
df_res = df_res.sort_values(['profit_factor', 'trades'], ascending=[False, False])

# Save full results
out_path = Path('/home/dy6z/workspace/binance-supertrend/grid_search_results.csv')
df_res.to_csv(out_path, index=False)
print(f"Saved full grid to {out_path}")

# Top 5 per symbol
print("\n=== TOP 5 PER SYMBOL ===")
for sym in SYMBOLS.keys():
    top5 = df_res[df_res['symbol']==sym].head(5)
    print(f"\n{sym}:")
    for _, r in top5.iterrows():
        print(f"  TP={r['tp_pct']*100:.1f}% SL={r['sl_pct']*100:.1f}% Lock={r['lock_pct']*100:.1f}% RWI={r['rwi']:.1f} | PF={r['profit_factor']:.2f} WR={r['win_rate']:.1f}% Trades={r['trades']} Eq={r['final_equity']}")
