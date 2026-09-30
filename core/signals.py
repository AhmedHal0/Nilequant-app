from __future__ import annotations


def signal(a: dict) -> dict:
    """Transparent score. Confidence is agreement of indicators, NOT P(profit)."""
    if not a:
        return {
            "score": 0,
            "confidence": 0,
            "label": "HOLD / WAIT",
            "label_ar": "انتظار / محايد",
            "reasons": ["لا توجد بيانات كافية."],
            "risk": "غير معروف",
            "levels": {},
        }
    score = 0
    reasons = []
    if a.get("trend") == "UP":
        score += 22
        reasons.append("SMA20 أعلى من SMA50 (اتجاه قصير صاعد).")
    elif a.get("trend") == "DOWN":
        score -= 22
        reasons.append("SMA20 أسفل SMA50 (اتجاه قصير هابط).")
    else:
        reasons.append("متوسطات الحركة غير مكتملة — بيانات غير كافية للاتجاه.")

    rsi = a.get("rsi")
    if rsi is None:
        reasons.append("RSI غير متاح.")
    elif rsi < 30:
        score += 16
        reasons.append("RSI في منطقة تشبع بيعي محتمل.")
    elif rsi < 45:
        score += 6
        reasons.append("RSI منخفض نسبيًا.")
    elif rsi > 70:
        score -= 16
        reasons.append("RSI مرتفع وقد يزيد خطر التصحيح.")
    elif rsi > 55:
        score += 6
        reasons.append("RSI يدعم الزخم الصاعد.")

    macd, sig = a.get("macd"), a.get("macd_signal")
    if macd is None or sig is None:
        reasons.append("MACD غير متاح.")
    elif macd > sig:
        score += 12
        reasons.append("MACD أعلى من خط الإشارة.")
    else:
        score -= 12
        reasons.append("MACD أسفل خط الإشارة.")

    last, s20 = a.get("last"), a.get("sma20")
    if last and s20:
        if last > s20:
            score += 8
            reasons.append("السعر فوق SMA20.")
        else:
            score -= 8
            reasons.append("السعر تحت SMA20.")

    if a.get("breakout"):
        score += 10
        reasons.append("كسر قرب أعلى 20 جلسة.")
    if a.get("breakdown"):
        score -= 10
        reasons.append("كسر قرب أدنى 20 جلسة.")

    vr = a.get("vol_ratio")
    if vr and vr > 1.5:
        reasons.append("حجم التداول أعلى من متوسط 20 يوم.")
        score += 4 if score > 0 else -4

    n_known = sum(1 for k in ("trend", "rsi", "macd") if a.get(k) not in (None, "INSUFFICIENT"))
    conf = min(90, max(40, 45 + abs(score) * 0.5 + n_known * 4))

    if score >= 28:
        label, label_ar = "BUY WATCH", "راقب شراء"
    elif score <= -28:
        label, label_ar = "REDUCE / SELL WATCH", "راقب تخفيف / بيع"
    else:
        label, label_ar = "HOLD / WAIT", "انتظار / محايد"

    p = float(a.get("last") or 0)
    at = float(a.get("atr") or (p * 0.02 if p else 0))
    risk = "مرتفع" if (a.get("atr_pct") or 0) > 4 else "متوسط" if (a.get("atr_pct") or 0) > 2 else "منخفض نسبيًا"
    levels = {
        "invalidation": round(p - 1.8 * at, 3) if p else None,
        "entry_zone_low": round(p - 0.4 * at, 3) if p else None,
        "entry_zone_high": round(p + 0.2 * at, 3) if p else None,
        "stop": round(p - 1.5 * at, 3) if p else None,
        "target1": round(p + 1.5 * at, 3) if p else None,
        "target2": round(p + 3 * at, 3) if p else None,
        "support": round(a.get("support") or 0, 3),
        "resistance": round(a.get("resistance") or 0, 3),
    }
    return {
        "score": score,
        "confidence": conf,
        "label": label,
        "label_ar": label_ar,
        "reasons": reasons,
        "risk": risk,
        "levels": levels,
        "disclaimer": "الثقة تقيس اتفاق المؤشرات وليست احتمال ربح.",
    }
