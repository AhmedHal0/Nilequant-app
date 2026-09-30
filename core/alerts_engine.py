from __future__ import annotations

from .alerts_store import list_alerts


def evaluate(alerts: list[dict] | None, analysis_by_symbol: dict, news_items: list[dict] | None = None) -> list[dict]:
    fired = []
    news_items = news_items or []
    for al in alerts if alerts is not None else list_alerts():
        if not al.get("enabled"):
            continue
        kind = al.get("kind")
        sym = (al.get("symbol") or "").upper()
        params = al.get("params") or {}
        a = analysis_by_symbol.get(sym) or {}
        hit = False
        detail = ""
        try:
            if kind == "price_above" and a.get("last") is not None:
                th = float(params.get("value", 0))
                hit = a["last"] >= th
                detail = f"السعر {a['last']} ≥ {th}"
            elif kind == "price_below" and a.get("last") is not None:
                th = float(params.get("value", 0))
                hit = a["last"] <= th
                detail = f"السعر {a['last']} ≤ {th}"
            elif kind == "rsi" and a.get("rsi") is not None:
                th = float(params.get("value", 70))
                op = params.get("op", "above")
                hit = a["rsi"] >= th if op == "above" else a["rsi"] <= th
                detail = f"RSI {a['rsi']:.1f}"
            elif kind == "macd_cross" and a.get("macd") is not None and a.get("macd_signal") is not None:
                hit = a["macd"] > a["macd_signal"]
                detail = "MACD فوق الإشارة" if hit else "MACD تحت الإشارة"
            elif kind == "sma_cross" and a.get("sma20") and a.get("sma50"):
                hit = a["sma20"] > a["sma50"]
                detail = "SMA20/50"
            elif kind == "breakout":
                hit = bool(a.get("breakout"))
                detail = "كسر 20 يوم"
            elif kind == "pct_move" and a.get("change_1d") is not None:
                th = float(params.get("value", 3))
                hit = abs(a["change_1d"]) >= th
                detail = f"تغير {a['change_1d']:.2f}%"
            elif kind in ("news_keyword", "favorite_news"):
                kw = (params.get("keyword") or "").lower()
                for n in news_items:
                    blob = ((n.get("title") or "") + " " + (n.get("summary") or "")).lower()
                    if kw and kw in blob:
                        hit = True
                        detail = n.get("title") or kw
                        break
                    if kind == "favorite_news" and n.get("symbol") == sym:
                        hit = True
                        detail = n.get("title") or ""
                        break
        except Exception:
            hit = False
        if hit:
            fired.append({**al, "detail": detail})
    return fired
