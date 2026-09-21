"""
FX Supertrend Strategy — Daily Long-Short
=========================================

Entry:
- Long: Supertrend(10,3) bullish + ADX(14) > 25
- Short: Supertrend(10,3) bearish + ADX(14) > 25

Exit:
- Supertrend flip (bullish → bearish atau sebaliknya)
- Stop loss: 2x ATR(14)

Universe: 19 G10 FX pairs
Max positions: 5 long + 5 short = 10 total
Timeframe: Daily
Account: 48397433 (cTrader demo long-short)
"""

# Symbol mapping ML4T → cTrader
SYMBOL_MAP = {
    "AUD_JPY": "AUDJPY", "AUD_NZD": "AUDNZD", "AUD_USD": "AUDUSD",
    "CAD_JPY": "CADJPY", "EUR_AUD": "EURAUD", "EUR_CAD": "EURCAD",
    "EUR_CHF": "EURCHF", "EUR_GBP": "EURGBP", "EUR_JPY": "EURJPY",
    "EUR_USD": "EURUSD", "GBP_AUD": "GBPAUD", "GBP_CHF": "GBPCHF",
    "GBP_JPY": "GBPJPY", "GBP_USD": "GBPUSD", "NZD_JPY": "NZDJPY",
    "NZD_USD": "NZDUSD", "USD_CAD": "USDCAD", "USD_CHF": "USDCHF",
    "USD_JPY": "USDJPY",
}

PAIRS = list(SYMBOL_MAP.keys())

# Account
ACCOUNT_ID = 48397433

# Strategy: RSI + EMA + Stochastic
# Validated backtest: +874% over 4 years (2022-2026), 244 trades, 55.3% win rate, PF 1.36
STRATEGY = "RSI_EMA_STOCHASTIC"

# Parameters
EMA_FAST = 20
EMA_SLOW = 50
RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
STOCH_PERIOD = 14
STOCH_OVERSOLD = 20
STOCH_OVERBOUGHT = 80
ATR_PERIOD = 14
SL_ATR_MULTIPLIER = 2.0

MAX_LONG = 5
MAX_SHORT = 5

# Execution
FIXED_LOT = 100000  # 1 standard lot (100k units)

# Pip sizes for P&L calculation (standard forex convention)
PIP_SIZES = {
    "AUD_JPY": 0.01, "AUD_NZD": 0.0001, "AUD_USD": 0.0001,
    "CAD_JPY": 0.01, "EUR_AUD": 0.0001, "EUR_CAD": 0.0001,
    "EUR_CHF": 0.0001, "EUR_GBP": 0.0001, "EUR_JPY": 0.01,
    "EUR_USD": 0.0001, "GBP_AUD": 0.0001, "GBP_CHF": 0.0001,
    "GBP_JPY": 0.01, "GBP_USD": 0.0001, "NZD_JPY": 0.01,
    "NZD_USD": 0.0001, "USD_CAD": 0.0001, "USD_CHF": 0.0001,
    "USD_JPY": 0.01,
}
