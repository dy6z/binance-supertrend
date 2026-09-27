import sys
sys.path.insert(0, '/home/dy6z/workspace/binance-supertrend')
import pandas as pd, numpy as np
from src.indicators import calculate_indicators

FEE = 0.0005 * 2  # 0.05% taker, both sides

def bt(df, tp, sl, lock, rwi, lev):
    pos = None; equity = 1.0; trades = 0; wins = 0; gp = 0.0; gl = 0.0
    dd_peak = 1.0; dd_max = 0.0
    for i in range(1, len(df)):
        row = df.iloc[i]; cp = float(row['close'])
        pnl = None
        if pos:
            side = pos['side']; entry = pos['entry']
            ret = (cp - entry) / entry if side == 'LONG' else (entry - cp) / entry
            if (side == 'LONG' and (ret >= tp or ret <= -sl)) or (side == 'SHORT' and (ret >= tp or ret <= -sl)):
                pnl = ret; pos = None
            elif side == 'LONG':
                sell_ok = bool(row['crossunder'] and row['rwiVal'] >= rwi and not row['nearSup'])
                if sell_ok and ret >= lock:
                    pnl = ret; pos = {'side': 'SHORT', 'entry': cp}
                elif row['crossunder']:
                    pnl = ret; pos = None
            elif side == 'SHORT':
                buy_ok = bool(row['crossover'] and row['rwiVal'] >= rwi and not row['nearRes'])
                if buy_ok and ret >= lock:
                    pnl = ret; pos = {'side': 'LONG', 'entry': cp}
                elif row['crossover']:
                    pnl = ret; pos = None
            if pnl is not None:
                trades += 1
                # Pure 1x, no fee — consistent with grid search & historical frozen backtests
                gp += max(pnl, 0); gl += min(pnl, 0)
                equity *= (1 + pnl)
                dd_peak = max(dd_peak, equity)
                dd_max = max(dd_max, (dd_peak - equity) / dd_peak)
                if pnl > 0:
                    wins += 1
        if pos is None:
            buy_ok = bool(row['crossover'] and row['rwiVal'] >= rwi and not row['nearRes'])
            sell_ok = bool(row['crossunder'] and row['rwiVal'] >= rwi and not row['nearSup'])
            if buy_ok: pos = {'side': 'LONG', 'entry': cp}
            elif sell_ok: pos = {'side': 'SHORT', 'entry': cp}
    pf = gp / abs(gl) if gl else float('inf')
    return dict(trades=trades, wr=round(wins / trades * 100, 1) if trades else 0,
                pf=round(pf, 3), ret=round((equity - 1) * 100, 1), maxdd=round(dd_max * 100, 1))

symdata = {
    'BTC':      ('/home/dy6z/workspace/binance-supertrend/frozen_60d/BTC.csv',      0.02,  0.02,  0.005, 1.2, 5),
    'SOL':      ('/home/dy6z/sol_data_frozen.csv',                                  0.015, 0.025, 0.01,  1.0, 10),
    'ZEC':      ('/home/dy6z/workspace/binance-supertrend/frozen_60d/ZEC.csv',       0.03,  0.02,  0.005, 1.0, 10),
    'SNDK':     ('/home/dy6z/workspace/binance-supertrend/frozen_60d/SNDK.csv',      0.01,  0.02,  0.005, 1.0, 10),
    '1000PEPE': ('/home/dy6z/workspace/binance-supertrend/frozen_60d/1000PEPE.csv',  0.02,  0.02,  0.005, 1.2, 10),
}

print(f"{'SYM':9}{'Candles':>8}{'Trades':>7}{'WR%':>6}{'PF':>7}{'Ret_1x%':>9}{'MaxDD%':>8}  params")
tot = 0
for sym, (path, tp, sl, lock, rwi, lev) in symdata.items():
    df = pd.read_csv(path)
    df.columns = [c.lower().replace(' ', '_') for c in df.columns]
    tscol = 'datetime' if 'datetime' in df.columns else 'timestamp'
    df[tscol] = pd.to_datetime(df[tscol])
    df = df.set_index(tscol).sort_index()[['open','high','low','close']].astype(float)
    df = calculate_indicators(df).dropna()
    r = bt(df, tp, sl, lock, rwi, lev)
    tot += r['trades']
    params = f"TP{tp*100:g}% SL{sl*100:g}% L{lock*100:g}% RWI{rwi} {lev}x"
    print(f"{sym:9}{len(df):>8}{r['trades']:>7}{r['wr']:>6}{r['pf']:>7}{r['ret']:>8}%{r['maxdd']:>7}%  {params}")
print(f"\nTotal trades: {tot}")
