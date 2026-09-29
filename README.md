# NileQuant — Egyptian market intelligence (production)

Arabic-first Streamlit app for EGX, gold, portfolio (Thndr CSV), news, briefing, backtests, and alerts.

**Storage:** SQLite (`data/nilequant.db` or `DATABASE_PATH`). Watchlist, transactions, alerts, settings, briefing/news/analysis caches persist across Streamlit reruns and process restarts **on the same disk**. Streamlit Community Cloud’s filesystem is not a durable disk; use a host with persistent volume for true production, or accept that the cloud instance may reset the file.

Never enter Thndr passwords, OTP, or cookies. Import CSV only.

Signals are research scores, not profit probabilities or advice.

## Schema (SQLite)

| Table | Purpose |
|---|---|
| `settings` | key/value (favorite_symbol, theme, cash_balance) |
| `watchlist` | persistent symbols |
| `transactions` | Thndr/manual trades |
| `alerts` | price/RSI/MACD/news rules |
| `daily_briefings` | saved briefing JSON |
| `news_cache` | query cache |
| `analysis_cache` | OHLCV JSON cache |

Positions are **derived** from `transactions` (no separate positions table).

## Secrets (Streamlit Cloud → Settings → Secrets)

```toml
EGXAPI_KEY = ""
EGXAPI_BASE_URL = "https://api.egxapi.com"
EGXAPI_ENV = "paper"
NEWS_API_KEY = ""
GOLD_SYMBOL = "GC=F"
LOCAL_GOLD_URL = ""
DATABASE_PATH = "/mount/nilequant.db"
```

| Secret | Required | Used for |
|---|---|---|
| `EGXAPI_KEY` | No | Live EGX bars; else Yahoo Finance |
| `NEWS_API_KEY` | No | NewsAPI; else Google News RSS |
| `LOCAL_GOLD_URL` | No | Egyptian retail gold JSON |
| `DATABASE_PATH` | No | SQLite file location |
| `GOLD_SYMBOL` | No | Default `GC=F` |

Do not rely on `.env` in production.

## Streamlit Cloud steps

1. Push **this folder** (`NileQuant_Complete`) as a GitHub repo root (so `app.py` is at repo root).
2. https://share.streamlit.io → New app → repo, branch, Main file `app.py`.
3. Advanced → Secrets → paste TOML above.
4. Deploy. URL: `https://<app-name>.streamlit.app`

## Local / tests

```bash
pip install -r requirements.txt
pytest -q
streamlit run app.py
```

Health: Settings page shows DB path and `SELECT 1`.

## Layout

- `app.py` — navigation only
- `core/` — db, market, news, analysis, signals, fundamentals, portfolio, backtest, briefing, alerts
- `ui/` — pages and charts
