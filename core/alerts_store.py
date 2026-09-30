from .db import connect, init_db, json_dumps, json_loads, utcnow


def list_alerts() -> list[dict]:
    init_db()
    with connect() as con:
        rows = con.execute(
            "SELECT id, kind, symbol, params, enabled, created_at FROM alerts ORDER BY id DESC"
        ).fetchall()
    out = []
    for r in rows:
        out.append(
            {
                "id": r["id"],
                "kind": r["kind"],
                "symbol": r["symbol"],
                "params": json_loads(r["params"], {}),
                "enabled": bool(r["enabled"]),
                "created_at": r["created_at"],
            }
        )
    return out


def add_alert(kind: str, symbol: str | None, params: dict) -> int:
    init_db()
    with connect() as con:
        cur = con.execute(
            "INSERT INTO alerts(kind, symbol, params, enabled, created_at) VALUES (?,?,?,?,?)",
            (kind, (symbol or "").upper() or None, json_dumps(params or {}), 1, utcnow()),
        )
        return int(cur.lastrowid)


def set_enabled(alert_id: int, enabled: bool) -> None:
    init_db()
    with connect() as con:
        con.execute("UPDATE alerts SET enabled=? WHERE id=?", (1 if enabled else 0, alert_id))


def delete_alert(alert_id: int) -> None:
    init_db()
    with connect() as con:
        con.execute("DELETE FROM alerts WHERE id=?", (alert_id,))
