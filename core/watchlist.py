from .db import connect, init_db, utcnow


def list_symbols() -> list[str]:
    init_db()
    with connect() as con:
        rows = con.execute("SELECT symbol FROM watchlist ORDER BY id").fetchall()
    return [r["symbol"] for r in rows]


def add_symbol(symbol: str) -> None:
    symbol = symbol.upper().strip()
    if not symbol:
        return
    init_db()
    with connect() as con:
        con.execute(
            "INSERT OR IGNORE INTO watchlist(symbol, added_at) VALUES (?, ?)",
            (symbol, utcnow()),
        )


def remove_symbol(symbol: str) -> None:
    init_db()
    with connect() as con:
        con.execute("DELETE FROM watchlist WHERE symbol=?", (symbol.upper().strip(),))
