from __future__ import annotations

from datetime import datetime, timezone

from .cache import save_briefing


def briefing(rows: list[dict], mode: str, news: list[dict] | None = None, portfolio_summary: dict | None = None) -> dict:
    title = "قبل الجلسة" if "قبل" in mode or mode == "pre" else "بعد الجلسة"
    table = []
    strong, weak, attention = [], [], []
    for r in rows:
        a, s = r.get("analysis") or {}, r.get("signal") or {}
        if not a:
            continue
        rec = {
            "السهم": r["symbol"],
            "السعر": round(a.get("last") or 0, 3),
            "اليومي%": round(a.get("change_1d") or 0, 2),
            "RSI": round(a["rsi"], 1) if a.get("rsi") is not None else None,
            "الإشارة": s.get("label_ar") or s.get("label"),
            "الثقة": round(s.get("confidence") or 0, 0),
            "المصدر": (r.get("meta") or {}).get("source"),
        }
        table.append(rec)
        sc = s.get("score") or 0
        if sc >= 28:
            strong.append(rec)
        elif sc <= -28:
            weak.append(rec)
        if abs(rec["اليومي%"]) >= 3 or a.get("breakout") or a.get("breakdown"):
            attention.append(rec)

    news = news or []
    news_bits = [{"title": n.get("title"), "impact": n.get("impact"), "source": n.get("source")} for n in news[:8]]
    text = f"## ملخص {title}\n\n"
    text += "تقرير آلي مبني على بيانات ومؤشرات متاحة. ليس توصية شراء/بيع وليس ضمانًا للاتجاه.\n\n"
    if "قبل" in title:
        text += "**طريقة القراءة:** رتب العناصر حسب توافق الأدلة، حدد وقفًا قبل أي قرار، ولا تطارد الافتتاح.\n"
    else:
        text += "**مراجعة الغد:** راقب تغيّر الإشارة، الأخبار ذات المصدر الواضح، وP/L المحفظة بدل سعر اليوم وحده.\n"
    text += f"\nآخر تحديث (UTC): {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}"
    out = {
        "text": text,
        "table": table,
        "strong": strong,
        "weak": weak,
        "attention": attention,
        "news": news_bits,
        "portfolio": portfolio_summary,
        "mode": title,
    }
    save_briefing(title, {k: v for k, v in out.items() if k != "table"})
    return out
