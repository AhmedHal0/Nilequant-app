"""Cloud market data: EGXAPI first, Yahoo Finance fallback. SQLite cache of OHLCV JSON."""
from __future__ import annotations

import os
from datetime import datetime, timezone

import pandas as pd
import requests
import yfinance as yf

from .cache import get_analysis, put_analysis


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class MarketData:
    def __init__(self):
        self.key = os.getenv("EGXAPI_KEY", "").strip()
        self.base = os.getenv("EGXAPI_BASE_URL", "https://api.egxapi.com").rstrip("/")
        self.env = os.getenv("EGXAPI_ENV", "paper")
        self.local_gold_url = os.getenv("LOCAL_GOLD_URL", "").strip()

    @property
    def has_api(self):
        return bool(self.key)

    def _api(self, symbol, period):
        if not self.key:
            return pd.DataFrame(), None
        try:
            r = requests.get(
                f"{self.base}/v2/market-data/bars",
                params={"symbol": symbol, "period": period},
                headers={"Authorization": f"Bearer {self.key}", "X-EGX-Env": self.env},
                timeout=15,
            )
            r.raise_for_status()
            d = r.json()
            rows = d.get("data", d)
            x = pd.DataFrame(rows)
            x = x.rename(
                columns={
                    "date": "Date",
                    "datetime": "Date",
                    "timestamp": "Date",
                    "open": "Open",
                    "high": "High",
                    "low": "Low",
                    "close": "Close",
                    "volume": "Volume",
                }
            )
            if not {"Date", "Open", "High", "Low", "Close"} <= set(x.columns):
                return pd.DataFrame(), None
            x["Date"] = pd.to_datetime(x.Date, errors="coerce")
            for c in ["Open", "High", "Low", "Close", "Volume"]:
                if c in x:
                    x[c] = pd.to_numeric(x[c], errors="coerce")
            x = x.dropna(subset=["Date", "Open", "High", "Low", "Close"]).sort_values("Date")
            return x.reset_index(drop=True), "EGXAPI"
        except Exception:
            return pd.DataFrame(), None

    def _yf(self, tickers, period):
        for t in tickers:
            try:
                x = yf.download(t, period=period, auto_adjust=False, progress=False)
                if x is None or x.empty:
                    continue
                if hasattr(x.columns, "levels"):
                    x.columns = x.columns.get_level_values(0)
                x = x.reset_index()
                cols = [c for c in ["Date", "Open", "High", "Low", "Close", "Volume"] if c in x]
                if len(cols) >= 5:
                    return x[cols].dropna().reset_index(drop=True), f"Yahoo Finance ({t})"
            except Exception:
                continue
        return pd.DataFrame(), None

    def history(self, symbol, period="1y", ttl=300):
        symbol = str(symbol).upper().strip()
        cached = get_analysis(symbol, f"ohlcv:{period}", ttl)
        if cached and cached.get("rows"):
            df = pd.DataFrame(cached["rows"])
            df["Date"] = pd.to_datetime(df["Date"])
            return df, {
                "source": cached.get("source", "cache"),
                "timestamp": cached.get("timestamp"),
                "freshness": "cached",
                "live": False,
            }
        df, src = self._api(symbol, period)
        freshness = "live" if src == "EGXAPI" else "historical"
        if df.empty:
            df, src = self._yf([symbol, f"{symbol}.CA"], period)
            freshness = "delayed/historical"
        meta = {
            "source": src or "unavailable",
            "timestamp": _now(),
            "freshness": freshness if src else "missing",
            "live": src == "EGXAPI",
        }
        if not df.empty:
            rows = df.copy()
            rows["Date"] = rows["Date"].astype(str)
            put_analysis(symbol, f"ohlcv:{period}", {"rows": rows.to_dict(orient="records"), **meta})
        return df, meta

    def gold_history(self, period="1y", ttl=300):
        return self.history(os.getenv("GOLD_SYMBOL", "GC=F"), period, ttl)

    def usd_egp(self, period="1y"):
        return self._yf(["EGP=X", "USDEGP=X"], period)

    def local_gold_reference(self):
        if not self.local_gold_url:
            return None, {
                "source": "not configured",
                "timestamp": _now(),
                "freshness": "missing",
                "note": "Set LOCAL_GOLD_URL for Egyptian retail gold. International futures are not local jewelry prices.",
            }
        try:
            r = requests.get(self.local_gold_url, timeout=12)
            r.raise_for_status()
            return r.json(), {"source": "LOCAL_GOLD_URL", "timestamp": _now(), "freshness": "live"}
        except Exception as e:
            return None, {"source": "LOCAL_GOLD_URL", "timestamp": _now(), "freshness": "error", "error": str(e)[:120]}
