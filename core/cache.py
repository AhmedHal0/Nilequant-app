from datetime import datetime, timezone, timedelta

from .db import connect, init_db, json_dumps, json_loads, utcnow


def _age_ok(fetched_at: str, ttl_sec: int) -> bool:
    try:
        t = datetime.strptime(fetched_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - t < timedelta(seconds=ttl_sec)
    except Exception:
        return False


def get_analysis(symbol: str, period: str, ttl_sec: int = 300):
    init_db()
    with connect() as con:
        row = con.execute(
            "SELECT payload, fetched_at FROM analysis_cache WHERE symbol=? AND period=?",
            (symbol.upper(), period),
        ).fetchone()
    if row and _age_ok(row["fetched_at"], ttl_sec):
        return json_loads(row["payload"])
    return None


def put_analysis(symbol: str, period: str, payload: dict) -> None:
    init_db()
    with connect() as con:
        con.execute(
            """INSERT INTO analysis_cache(symbol, period, payload, fetched_at)
               VALUES (?,?,?,?)
               ON CONFLICT(symbol, period) DO UPDATE SET payload=excluded.payload, fetched_at=excluded.fetched_at""",
            (symbol.upper(), period, json_dumps(payload), utcnow()),
        )


def get_news(query: str, ttl_sec: int = 600):
    init_db()
    with connect() as con:
        row = con.execute(
            "SELECT payload, fetched_at FROM news_cache WHERE query=? ORDER BY id DESC LIMIT 1",
            (query,),
        ).fetchone()
    if row and _age_ok(row["fetched_at"], ttl_sec):
        return json_loads(row["payload"], [])
    return None


def put_news(query: str, payload) -> None:
    init_db()
    with connect() as con:
        con.execute(
            "INSERT INTO news_cache(query, payload, fetched_at) VALUES (?,?,?)",
            (query, json_dumps(payload), utcnow()),
        )


def save_briefing(mode: str, content: dict) -> None:
    init_db()
    with connect() as con:
        con.execute(
            "INSERT INTO daily_briefings(mode, content, created_at) VALUES (?,?,?)",
            (mode, json_dumps(content), utcnow()),
        )


def latest_briefing(mode: str):
    init_db()
    with connect() as con:
        row = con.execute(
            "SELECT content, created_at FROM daily_briefings WHERE mode=? ORDER BY id DESC LIMIT 1",
            (mode,),
        ).fetchone()
    if not row:
        return None
    data = json_loads(row["content"], {})
    data["created_at"] = row["created_at"]
    return data
