from __future__ import annotations

import numpy as np
import pandas as pd


def rsi(c, n=14):
    d = c.diff()
    u = d.clip(lower=0)
    dn = -d.clip(upper=0)
    au = u.ewm(alpha=1 / n, adjust=False).mean()
    ad = dn.ewm(alpha=1 / n, adjust=False).mean()
    rs = au / ad.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def atr(x, n=14):
    p = x.Close.shift()
    tr = pd.concat([x.High - x.Low, (x.High - p).abs(), (x.Low - p).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def analyze(df: pd.DataFrame, bench: pd.DataFrame | None = None) -> dict:
    x = df.copy()
    if x.empty or "Close" not in x:
        return {}
    for n in [20, 50, 200]:
        x[f"SMA{n}"] = x.Close.rolling(n).mean()
    x["EMA12"] = x.Close.ewm(span=12, adjust=False).mean()
    x["EMA26"] = x.Close.ewm(span=26, adjust=False).mean()
    x["EMA50"] = x.Close.ewm(span=50, adjust=False).mean()
    x["MACD"] = x.EMA12 - x.EMA26
    x["MACDSignal"] = x.MACD.ewm(span=9, adjust=False).mean()
    x["MACDHist"] = x.MACD - x.MACDSignal
    x["RSI"] = rsi(x.Close)
    x["ATR"] = atr(x)
    if "Volume" in x:
        x["VolSMA20"] = x.Volume.rolling(20).mean()
        x["vol_ratio"] = x.Volume / x.VolSMA20.replace(0, np.nan)
    else:
        x["vol_ratio"] = np.nan
    x["high20"] = x.High.rolling(20).max()
    x["low20"] = x.Low.rolling(20).min()
    x["mom20"] = x.Close.pct_change(20)
    l = x.iloc[-1]
    p = x.iloc[-2] if len(x) > 1 else l
    sma20, sma50, sma200 = l.get("SMA20"), l.get("SMA50"), l.get("SMA200")
    if pd.notna(sma20) and pd.notna(sma50) and sma20 > sma50:
        trend = "UP"
    elif pd.notna(sma20) and pd.notna(sma50):
        trend = "DOWN"
    else:
        trend = "INSUFFICIENT"
    if pd.notna(sma200):
        trend_long = "UP" if l.Close > sma200 else "DOWN"
    else:
        trend_long = "INSUFFICIENT"
    support = float(l.low20) if pd.notna(l.low20) else float(x.Low.min())
    resistance = float(l.high20) if pd.notna(l.high20) else float(x.High.max())
    breakout = bool(pd.notna(l.high20) and l.Close >= l.high20 * 0.998)
    breakdown = bool(pd.notna(l.low20) and l.Close <= l.low20 * 1.002)
    vol = float(l.ATR / l.Close * 100) if pd.notna(l.ATR) and l.Close else None
    rel = None
    if bench is not None and not bench.empty and len(bench) > 20 and len(x) > 20:
        try:
            a = x.Close.pct_change(20).iloc[-1]
            b = bench.Close.pct_change(20).iloc[-1]
            if pd.notna(a) and pd.notna(b):
                rel = float(a - b) * 100
        except Exception:
            rel = None
    last = float(l.Close)
    prev = float(p.Close) if p.Close else last
    return {
        "frame": x,
        "last": last,
        "change_1d": float((last / prev - 1) * 100) if prev else 0.0,
        "rsi": float(l.RSI) if pd.notna(l.RSI) else None,
        "atr": float(l.ATR) if pd.notna(l.ATR) else None,
        "atr_pct": vol,
        "trend": trend,
        "trend_long": trend_long,
        "macd": float(l.MACD) if pd.notna(l.MACD) else None,
        "macd_signal": float(l.MACDSignal) if pd.notna(l.MACDSignal) else None,
        "macd_hist": float(l.MACDHist) if pd.notna(l.MACDHist) else None,
        "vol_ratio": float(l.vol_ratio) if pd.notna(l.get("vol_ratio")) else None,
        "support": support,
        "resistance": resistance,
        "breakout": breakout,
        "breakdown": breakdown,
        "momentum_20": float(l.mom20) * 100 if pd.notna(l.mom20) else None,
        "relative_strength_20": rel,
        "sma20": float(sma20) if pd.notna(sma20) else None,
        "sma50": float(sma50) if pd.notna(sma50) else None,
        "sma200": float(sma200) if pd.notna(sma200) else None,
        "ema12": float(l.EMA12) if pd.notna(l.EMA12) else None,
    }
