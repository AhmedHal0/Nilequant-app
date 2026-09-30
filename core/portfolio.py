"""Persistent Thndr/manual transactions in SQLite. Positions derived from trades."""
from __future__ import annotations

import pandas as pd

from .db import connect, init_db, utcnow

COLS = ["date", "symbol", "side", "quantity", "price", "fees", "source"]


def add_transaction(date, symbol, side, quantity, price, fees=0.0, source="manual") -> None:
    init_db()
    with connect() as con:
        con.execute(
            """INSERT INTO transactions(date, symbol, side, quantity, price, fees, source, created_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                str(date),
                str(symbol).upper().strip(),
                str(side).upper().strip(),
                float(quantity),
                float(price),
                float(fees or 0),
                source,
                utcnow(),
            ),
        )


def import_df(df: pd.DataFrame, source="thndr_csv") -> int:
    if df is None or df.empty:
        return 0
    z = df.copy()
    z.columns = [str(c).lower().strip() for c in z.columns]
    mapping = {}
    for c in z.columns:
        if c in ("date", "trade date", "التاريخ"):
            mapping[c] = "date"
        elif c in ("symbol", "ticker", "السهم"):
            mapping[c] = "symbol"
        elif c in ("side", "type", "action", "النوع"):
            mapping[c] = "side"
        elif c in ("quantity", "qty", "shares", "الكمية"):
            mapping[c] = "quantity"
        elif c in ("price", "avg price", "السعر"):
            mapping[c] = "price"
        elif c in ("fees", "commission", "الرسوم"):
            mapping[c] = "fees"
    z = z.rename(columns=mapping)
    n = 0
    for _, r in z.iterrows():
        try:
            side = str(r.get("side", "BUY")).upper()
            if side in ("شراء", "BUY", "B"):
                side = "BUY"
            elif side in ("بيع", "SELL", "S"):
                side = "SELL"
            else:
                continue
            add_transaction(
                r.get("date", ""),
                r.get("symbol", ""),
                side,
                float(r.get("quantity", 0) or 0),
                float(r.get("price", 0) or 0),
                float(r.get("fees", 0) or 0),
                source,
            )
            n += 1
        except Exception:
            continue
    return n


def load_transactions() -> pd.DataFrame:
    init_db()
    with connect() as con:
        rows = con.execute(
            "SELECT id, date, symbol, side, quantity, price, fees, source, created_at FROM transactions ORDER BY date, id"
        ).fetchall()
    if not rows:
        return pd.DataFrame(columns=["id"] + COLS + ["created_at"])
    return pd.DataFrame([dict(r) for r in rows])


def positions() -> pd.DataFrame:
    x = load_transactions()
    out = []
    if x.empty:
        return pd.DataFrame(columns=["symbol", "quantity", "avg_cost", "fees_open", "invested"])
    for sym, g in x.groupby("symbol"):
        q = cost = fees_open = 0.0
        for _, r in g.sort_values(["date", "id"]).iterrows():
            if r.side == "BUY":
                cost += r.quantity * r.price + r.fees
                fees_open += r.fees
                q += r.quantity
            elif r.side == "SELL" and q:
                avg = cost / q if q else 0
                q -= r.quantity
                cost = max(0.0, q * avg)
        if q > 1e-9:
            out.append(
                {
                    "symbol": sym,
                    "quantity": q,
                    "avg_cost": cost / q,
                    "fees_open": fees_open,
                    "invested": cost,
                }
            )
    return pd.DataFrame(out)


def realized_pl() -> float:
    x = load_transactions()
    if x.empty:
        return 0.0
    total = 0.0
    for _, g in x.groupby("symbol"):
        lots = []
        for _, r in g.sort_values(["date", "id"]).iterrows():
            if r.side == "BUY":
                lots.append({"q": float(r.quantity), "cost": float(r.price), "fees": float(r.fees)})
            elif r.side == "SELL":
                need = float(r.quantity)
                proceeds = need * float(r.price) - float(r.fees)
                cost_basis = 0.0
                while need > 1e-9 and lots:
                    lot = lots[0]
                    take = min(lot["q"], need)
                    cost_basis += take * lot["cost"] + lot["fees"] * (take / lot["q"] if lot["q"] else 0)
                    lot["q"] -= take
                    need -= take
                    if lot["q"] <= 1e-9:
                        lots.pop(0)
                total += proceeds - cost_basis
    return total


def summary(last_prices: dict[str, float], cash: float = 0.0, prev_value: float | None = None) -> dict:
    pos = positions()
    tx = load_transactions()
    invested = float(tx.loc[tx.side == "BUY", "quantity"].mul(tx.loc[tx.side == "BUY", "price"]).sum()) if not tx.empty else 0.0
    fees = float(tx["fees"].sum()) if not tx.empty else 0.0
    mkt = 0.0
    unreal = 0.0
    rows = []
    it = pos.iterrows() if not pos.empty else []
    for _, r in it:
        last = float(last_prices.get(r.symbol, r.avg_cost))
        value = last * r.quantity
        cost = r.avg_cost * r.quantity
        mkt += value
        unreal += value - cost
        rows.append({**r.to_dict(), "last": last, "value": value, "unrealized": value - cost})
    total_value = mkt + cash
    ret_pct = ((total_value - cash - (invested - realized_pl() - fees)) / invested * 100) if invested else 0.0
    # simpler: market + cash vs invested + cash start; use invested as cost of remaining + realized
    cost_open = float(pos["invested"].sum()) if not pos.empty else 0.0
    ret_pct = ((mkt - cost_open + realized_pl()) / cost_open * 100) if cost_open else 0.0
    daily = None
    if prev_value is not None:
        daily = total_value - prev_value
    return {
        "total_invested": invested,
        "available_cash": cash,
        "total_fees": fees,
        "realized_pl": realized_pl(),
        "unrealized_pl": unreal,
        "total_portfolio_value": total_value,
        "return_pct": ret_pct,
        "daily_pl": daily,
        "positions": rows,
        "open_cost": cost_open,
    }
