import os
import tempfile
from pathlib import Path

import pandas as pd
import pytest

# isolate DB before importing engines
os.environ["DATABASE_PATH"] = str(Path(tempfile.gettempdir()) / "nilequant_test.db")
try:
    Path(os.environ["DATABASE_PATH"]).unlink()
except FileNotFoundError:
    pass

from core.analysis import analyze
from core.backtest import backtest
from core.db import init_db, set_setting, get_setting
from core.health import check
from core.portfolio import add_transaction, positions, summary, import_df, realized_pl
from core.signals import signal
from core.watchlist import add_symbol, list_symbols, remove_symbol
from core.alerts_store import add_alert, list_alerts
from core.alerts_engine import evaluate
from core.briefing import briefing


def _ohlc(n=80):
    close = pd.Series(range(1, n + 1), dtype=float)
    return pd.DataFrame(
        {
            "Date": pd.date_range("2020-01-01", periods=n),
            "Open": close,
            "High": close + 1,
            "Low": close - 1,
            "Close": close,
            "Volume": [1000] * n,
        }
    )


def test_db_health():
    init_db()
    h = check()
    assert h["ok"] is True


def test_watchlist_persists():
    add_symbol("TEST")
    assert "TEST" in list_symbols()
    remove_symbol("TEST")
    assert "TEST" not in list_symbols()


def test_settings():
    set_setting("favorite_symbol", "COMI")
    assert get_setting("favorite_symbol") == "COMI"


def test_portfolio_avg_and_pl():
    add_transaction("2024-01-01", "COMI", "BUY", 10, 10, 0)
    add_transaction("2024-02-01", "COMI", "BUY", 10, 20, 0)
    pos = positions()
    row = pos[pos.symbol == "COMI"].iloc[0]
    assert abs(row.avg_cost - 15) < 1e-6
    add_transaction("2024-03-01", "COMI", "SELL", 10, 30, 0)
    assert realized_pl() > 0
    sm = summary({"COMI": 25}, cash=100)
    assert sm["available_cash"] == 100
    assert sm["unrealized_pl"] != 0 or sm["realized_pl"] != 0


def test_thndr_import():
    df = pd.DataFrame(
        {"date": ["2024-06-01"], "symbol": ["SWDY"], "side": ["BUY"], "quantity": [5], "price": [2], "fees": [0.1]}
    )
    n = import_df(df)
    assert n == 1
    assert "SWDY" in list(positions()["symbol"].values)


def test_analysis_and_signal():
    a = analyze(_ohlc())
    assert a["last"] == 80
    assert a["trend"] in ("UP", "DOWN", "INSUFFICIENT")
    s = signal(a)
    assert s["label"] in ("BUY WATCH", "HOLD / WAIT", "REDUCE / SELL WATCH")
    assert "احتمال" not in s["disclaimer"] or "ليست" in s["disclaimer"]


def test_signal_empty():
    s = signal({})
    assert s["label"] == "HOLD / WAIT"


def test_backtest_sma():
    r = backtest(_ohlc(200), "sma", 10, 30, fee_bps=10, slip_bps=5)
    assert "return_pct" in r
    assert r["trades"] >= 0
    assert len(r["equity"]) == 200


def test_alerts():
    add_alert("price_above", "COMI", {"value": 1})
    fired = evaluate(list_alerts(), {"COMI": {"last": 10}})
    assert any(x["kind"] == "price_above" for x in fired)


def test_briefing():
    a = analyze(_ohlc())
    s = signal(a)
    b = briefing([{"symbol": "COMI", "analysis": a, "signal": s, "meta": {"source": "test"}}], "pre")
    assert b["table"]
