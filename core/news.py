from __future__ import annotations

import os
from datetime import datetime, timezone
from urllib.parse import quote_plus

import feedparser
import requests

from .cache import get_news, put_news

NEG = ("cut", "loss", "fine", "probe", "crash", "sanction", "inflation spike", "devalu", "هبوط", "خسارة", "غرامة")
POS = ("profit", "growth", "raise", "upgrade", "record", "dividend", "expand", "ارتفاع", "أرباح", "توزيع")


def _classify(text: str) -> tuple[str, str]:
    t = (text or "").lower()
    p = sum(1 for w in POS if w in t)
    n = sum(1 for w in NEG if w in t)
    if p and not n:
        return "positive", "كلمات إيجابية ظاهرة في العنوان/الملخص — تصنيف آلي سطحي وليس حكمًا على السوق."
    if n and not p:
        return "negative", "كلمات سلبية ظاهرة في العنوان/الملخص — تصنيف آلي سطحي وليس حكمًا على السوق."
    if p and n:
        return "mixed", "إشارات مختلطة في النص؛ لا يُستنتج اتجاه."
    return "neutral", "لا توجد كلمات أثر واضحة؛ يُصنَّف محايدًا دون اختراع معنويات."


def _guess_symbol(text: str, watch: list[str]) -> str | None:
    u = (text or "").upper()
    for s in watch or []:
        if s and s.upper() in u:
            return s.upper()
    return None


class NewsService:
    def __init__(self):
        self.key = os.getenv("NEWS_API_KEY", "").strip()

    @property
    def has_api(self):
        return bool(self.key)

    def search(self, q: str, watch: list[str] | None = None, ttl=600) -> list[dict]:
        cached = get_news(q, ttl)
        if cached is not None:
            return cached
        out = []
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        if self.key:
            try:
                d = requests.get(
                    "https://newsapi.org/v2/everything",
                    params={"q": q, "sortBy": "publishedAt", "pageSize": 30, "apiKey": self.key},
                    timeout=12,
                ).json()
                if d.get("status") == "ok":
                    for x in d.get("articles") or []:
                        title = x.get("title") or ""
                        summary = x.get("description") or ""
                        impact, why = _classify(title + " " + summary)
                        out.append(
                            {
                                "title": title,
                                "summary": summary,
                                "source": (x.get("source") or {}).get("name") or "NewsAPI",
                                "published": x.get("publishedAt") or "",
                                "link": x.get("url") or "",
                                "symbol": _guess_symbol(title + " " + summary, watch or []),
                                "impact": impact,
                                "impact_note": why,
                                "fetched_at": ts,
                                "provider": "NewsAPI",
                            }
                        )
            except Exception:
                pass
        if not out:
            try:
                f = feedparser.parse(
                    f"https://news.google.com/rss/search?q={quote_plus(q)}&hl=ar&gl=EG&ceid=EG:ar"
                )
                for x in f.entries:
                    title = x.get("title") or ""
                    summary = x.get("summary") or ""
                    impact, why = _classify(title + " " + summary)
                    out.append(
                        {
                            "title": title,
                            "summary": summary,
                            "source": getattr(x, "source", None) and getattr(x.source, "title", None) or "Google News",
                            "published": x.get("published") or "",
                            "link": x.get("link") or "",
                            "symbol": _guess_symbol(title + " " + summary, watch or []),
                            "impact": impact,
                            "impact_note": why,
                            "fetched_at": ts,
                            "provider": "Google News RSS",
                        }
                    )
            except Exception:
                pass
        put_news(q, out)
        return out

    def monitor_bundle(self, watch: list[str]) -> dict:
        topics = {
            "egx": "EGX البورصة المصرية",
            "cbe": "البنك المركزي المصري CBE interest rate",
            "egp": "USD EGP الجنيه المصري",
            "gold": "gold الذهب مصر",
            "global": "global stocks Federal Reserve oil",
        }
        data = {k: self.search(q, watch)[:12] for k, q in topics.items()}
        companies = []
        for s in watch[:8]:
            companies.extend(self.search(f"{s} Egypt stock", watch)[:4])
        data["companies"] = companies
        return data
