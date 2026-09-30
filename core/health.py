from .db import db_path, init_db, connect


def check() -> dict:
    path = init_db()
    ok = True
    err = None
    try:
        with connect() as con:
            con.execute("SELECT 1").fetchone()
    except Exception as e:
        ok = False
        err = str(e)
    return {"ok": ok, "database": str(path), "error": err}
