"""Fundamentals from Yahoo when present. Never invent numbers."""
from __future__ import annotations

from datetime import datetime, timezone

import yfinance as yf


def _na(v):
    if v is None:
        return None
    try:
        if v != v:  # NaN
            return None
    except Exception:
        pass
    return v


def fundamentals(symbol: str) -> dict:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    info = {}
    source = "unavailable"
    try:
        t = yf.Ticker(symbol)
        info = t.info or {}
        if not info:
            t2 = yf.Ticker(f"{symbol}.CA")
            info = t2.info or {}
            if info:
                source = "Yahoo Finance (.CA)"
        else:
            source = "Yahoo Finance"
    except Exception as e:
        return {
            "available": False,
            "fields": {},
            "source": "error",
            "timestamp": ts,
            "note": str(e)[:160],
        }

    keys = {
        "pe": "trailingPE",
        "pb": "priceToBook",
        "eps": "trailingEps",
        "dividend_yield": "dividendYield",
        "revenue_growth": "revenueGrowth",
        "earnings_growth": "earningsGrowth",
        "profit_margin": "profitMargins",
        "operating_margin": "operatingMargins",
        "roe": "returnOnEquity",
        "debt_to_equity": "debtToEquity",
        "total_debt": "totalDebt",
        "sector": "sector",
        "industry": "industry",
        "long_name": "longName",
    }
    fields = {}
    any_ok = False
    for label, k in keys.items():
        v = _na(info.get(k))
        fields[label] = {"value": v, "available": v is not None}
        if v is not None:
            any_ok = True
    if not any_ok:
        source = "unavailable"
    return {
        "available": any_ok,
        "fields": fields,
        "source": source,
        "timestamp": ts,
        "note": None if any_ok else "لا تتوفر أساسيات موثوقة لهذا الرمز من المصدر الحالي.",
    }


def display_value(field: dict, pct=False, nd=2) -> str:
    if not field or not field.get("available"):
        return "غير متاح"
    v = field["value"]
    try:
        if pct:
            return f"{float(v) * 100:.{nd}f}%"
        return f"{float(v):.{nd}f}"
    except Exception:
        return str(v)
