from __future__ import annotations

import numpy as np
import pandas as pd

from .analysis import rsi as rsi_series


def _metrics(equity: pd.Series, bh: pd.Series, trades: int, wins: int, gp: float, gl: float, dates) -> dict:
    eq = equity.dropna()
    if eq.empty:
        return {
            "return_pct": 0,
            "buy_hold_pct": 0,
            "cagr": None,
            "max_drawdown_pct": 0,
            "sharpe": None,
            "win_rate": None,
            "profit_factor": None,
            "trades": 0,
            "equity": pd.DataFrame({"Date": dates, "equity": equity}),
        }
    ret = float(eq.iloc[-1] / eq.iloc[0] - 1) * 100
    bh_pct = float(bh.iloc[-1] / bh.iloc[0] - 1) * 100 if bh.iloc[0] else 0
    peak = eq.cummax()
    dd = float((eq / peak - 1).min() * 100)
    daily = eq.pct_change().dropna()
    sharpe = None
    if len(daily) > 5 and daily.std() > 0:
        sharpe = float(np.sqrt(252) * daily.mean() / daily.std())
    years = None
    try:
        d0, d1 = pd.to_datetime(dates.iloc[0]), pd.to_datetime(dates.iloc[-1])
        years = max((d1 - d0).days / 365.25, 1e-6)
    except Exception:
        years = None
    cagr = None
    if years and years >= 0.6 and eq.iloc[0]:
        cagr = float((eq.iloc[-1] / eq.iloc[0]) ** (1 / years) - 1) * 100
    wr = (wins / trades * 100) if trades else None
    pf = (gp / abs(gl)) if gl else (None if gp == 0 else float("inf"))
    return {
        "return_pct": ret,
        "buy_hold_pct": bh_pct,
        "cagr": cagr,
        "max_drawdown_pct": dd,
        "sharpe": sharpe,
        "win_rate": wr,
        "profit_factor": pf if pf != float("inf") else None,
        "trades": trades,
        "equity": pd.DataFrame({"Date": dates, "equity": equity}),
    }


def backtest(df: pd.DataFrame, strategy="sma", fast=20, slow=50, rsi_buy=30, rsi_sell=70, fee_bps=10, slip_bps=5) -> dict:
    x = df.copy().reset_index(drop=True)
    if x.empty or "Close" not in x:
        return _metrics(pd.Series(dtype=float), pd.Series(dtype=float), 0, 0, 0, 0, pd.Series(dtype=object))
    cost = (fee_bps + slip_bps) / 10000
    close = x.Close.astype(float)
    if strategy == "sma":
        f = close.rolling(fast).mean()
        s = close.rolling(slow).mean()
        pos = (f > s).astype(float)
    elif strategy == "rsi":
        r = rsi_series(close)
        pos = pd.Series(np.nan, index=x.index)
        state = 0.0
        for i, v in enumerate(r.fillna(50)):
            if v < rsi_buy:
                state = 1.0
            elif v > rsi_sell:
                state = 0.0
            pos.iloc[i] = state
    elif strategy == "macd":
        e12 = close.ewm(span=12, adjust=False).mean()
        e26 = close.ewm(span=26, adjust=False).mean()
        macd = e12 - e26
        sig = macd.ewm(span=9, adjust=False).mean()
        pos = (macd > sig).astype(float)
    elif strategy == "breakout":
        hh = x.High.rolling(20).max().shift(1)
        pos = (close > hh).astype(float)
    else:  # trend following SMA50
        sma = close.rolling(50).mean()
        pos = (close > sma).astype(float)
    ret = close.pct_change().fillna(0)
    chg = pos.diff().abs().fillna(0)
    strat = ret * pos.shift(1).fillna(0) - chg * cost
    equity = (1 + strat).cumprod()
    trades = int(chg.sum() / 2)
    # trade stats from round trips
    wins = gp = gl = 0.0
    entry = None
    for i in range(len(pos)):
        if i == 0:
            continue
        if pos.iloc[i] == 1 and pos.iloc[i - 1] == 0:
            entry = close.iloc[i]
        elif pos.iloc[i] == 0 and pos.iloc[i - 1] == 1 and entry:
            pnl = close.iloc[i] / entry - 1 - 2 * cost
            if pnl > 0:
                wins += 1
                gp += pnl
            else:
                gl += pnl
            entry = None
    return _metrics(equity, close, trades, int(wins), float(gp), float(gl), x.Date)
