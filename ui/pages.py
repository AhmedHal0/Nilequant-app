from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from core import alerts_store, portfolio, watchlist
from core.alerts_engine import evaluate
from core.analysis import analyze
from core.backtest import backtest
from core.briefing import briefing
from core.db import get_setting, set_setting
from core.fundamentals import display_value, fundamentals
from core.health import check as health_check
from core.market_data import MarketData
from core.news import NewsService
from core.signals import signal
from ui.charts import candle

NAV = [
    "لوحة التحكم",
    "السوق",
    "تحليل سهم",
    "السهم المفضل",
    "المحفظة",
    "الذهب",
    "الأخبار",
    "التقرير اليومي",
    "الاختبار التاريخي",
    "إدارة المخاطر",
    "التنبيهات",
    "الإعدادات",
]


def _meta_caption(meta: dict):
    if not meta:
        st.caption("المصدر: غير متاح")
        return
    st.caption(
        f"المصدر: {meta.get('source')} • الوقت: {meta.get('timestamp')} • الحالة: {meta.get('freshness')}"
    )


def _load_symbol(market: MarketData, sym: str, period="1y", bench=None):
    df, meta = market.history(sym, period)
    if df.empty:
        return None, None, None, meta
    a = analyze(df, bench)
    s = signal(a)
    return df, a, s, meta


def page_dashboard(market, news, watch):
    st.title("NileQuant")
    st.caption("مركز متابعة البورصة المصرية والذهب والمحفظة — إشارات بحثية وليست توصية.")
    cols = st.columns(min(5, max(1, len(watch))))
    rows = []
    analysis_map = {}
    for i, sym in enumerate(watch[:5]):
        df, a, s, meta = _load_symbol(market, sym, "6mo")
        if a:
            analysis_map[sym] = a
            cols[i].metric(sym, f"{a['last']:.2f}", f"{a['change_1d']:+.2f}%")
            cols[i].caption(f"{s['label_ar']} • ثقة مؤشرات {s['confidence']:.0f}%")
            rows.append(
                {
                    "السهم": sym,
                    "السعر": round(a["last"], 3),
                    "اليومي %": round(a["change_1d"], 2),
                    "RSI": None if a["rsi"] is None else round(a["rsi"], 1),
                    "الاتجاه": a["trend"],
                    "الإشارة": s["label_ar"],
                    "المصدر": meta.get("source"),
                }
            )
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    fired = evaluate(None, analysis_map, [])
    if fired:
        st.warning("تنبيهات نشطة: " + " • ".join(f"{x['kind']} {x.get('symbol')}" for x in fired[:6]))
    st.info("لا يوجد نموذج يضمن توقيت السوق. النظام يعرض أدلة متعددة ودرجة اتفاق ومخاطر.")


def page_market(market, watch):
    st.title("السوق")
    period = st.selectbox("الفترة", ["3mo", "6mo", "1y", "2y"], 2)
    rows = []
    for sym in watch:
        df, a, s, meta = _load_symbol(market, sym, period)
        if not a:
            rows.append({"السهم": sym, "الحالة": "بيانات ناقصة", "المصدر": meta.get("source")})
            continue
        rows.append(
            {
                "السهم": sym,
                "السعر": round(a["last"], 3),
                "اليومي%": round(a["change_1d"], 2),
                "SMA20": a["sma20"],
                "RSI": a["rsi"],
                "كسر": "نعم" if a["breakout"] else "لا",
                "الإشارة": s["label"],
                "المصدر": meta.get("source"),
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def page_analysis(market, news, watch):
    st.title("تحليل سهم")
    sym = st.text_input("رمز السهم", watch[0] if watch else "COMI").upper().strip()
    period = st.selectbox("الفترة", ["3mo", "6mo", "1y", "2y", "5y"], 2)
    df, a, s, meta = _load_symbol(market, sym, period)
    _meta_caption(meta)
    if not a:
        st.error("لا توجد بيانات كافية. لم يُختلق أي سعر.")
        return
    st.markdown(f"**{s['label']}** — {s['label_ar']} | الدرجة {s['score']:+.0f} | اتفاق المؤشرات {s['confidence']:.0f}%")
    st.caption(s["disclaimer"])
    c = st.columns(5)
    c[0].metric("السعر", f"{a['last']:.3f}")
    c[1].metric("RSI", "غير متاح" if a["rsi"] is None else f"{a['rsi']:.1f}")
    c[2].metric("ATR %", "غير متاح" if a["atr_pct"] is None else f"{a['atr_pct']:.2f}%")
    c[3].metric("MACD", "غير متاح" if a["macd"] is None else f"{a['macd']:.3f}")
    c[4].metric("Trend", a["trend"])
    st.plotly_chart(candle(a["frame"], sym), use_container_width=True)
    st.subheader("أسباب الإشارة")
    for x in s["reasons"]:
        st.write("•", x)
    st.write("المخاطر:", s["risk"])
    st.subheader("مستويات مرجعية (ليست أوامر)")
    st.dataframe(pd.DataFrame([s["levels"]]), use_container_width=True, hide_index=True)
    st.subheader("أساسيات")
    fun = fundamentals(sym)
    st.caption(f"المصدر: {fun['source']} • {fun['timestamp']}")
    if not fun["available"]:
        st.write(fun["note"])
    else:
        f = fun["fields"]
        st.write(
            {
                "P/E": display_value(f["pe"]),
                "P/B": display_value(f["pb"]),
                "EPS": display_value(f["eps"]),
                "عائد التوزيع": display_value(f["dividend_yield"], True),
                "نمو الإيرادات": display_value(f["revenue_growth"], True),
                "نمو الأرباح": display_value(f["earnings_growth"], True),
                "هامش الربح": display_value(f["profit_margin"], True),
                "ROE": display_value(f["roe"], True),
                "الدين/حقوق الملكية": display_value(f["debt_to_equity"]),
                "القطاع": f["sector"]["value"] if f["sector"]["available"] else "غير متاح",
            }
        )
    st.subheader("أخبار")
    for x in news.search(sym + " Egypt stock", watch)[:8]:
        st.markdown(f"**{x['title']}**")
        st.caption(f"{x['source']} • {x['published']} • أثر آلي: {x['impact']}")
        st.write(x.get("impact_note"))
        if x.get("link"):
            st.link_button("فتح", x["link"])


def page_favorite(market, news, watch):
    st.title("السهم المفضل")
    fav = get_setting("favorite_symbol", watch[0] if watch else "COMI")
    options = watch or [fav]
    idx = options.index(fav) if fav in options else 0
    sym = st.selectbox("اختر السهم", options, index=idx)
    if st.button("حفظ كسهم مفضل"):
        set_setting("favorite_symbol", sym)
        st.success("حُفظ في قاعدة البيانات")
    df, a, s, meta = _load_symbol(market, sym, "2y")
    _meta_caption(meta)
    if not a:
        st.error("بيانات ناقصة.")
        return
    if s["score"] >= 20:
        thesis = "Evidence currently supports a constructive technical backdrop."
        ar = "الأدلة الحالية تدعم خلفية فنية بنّاءة نسبيًا."
    elif s["score"] <= -20:
        thesis = "Risks have increased relative to recent technical evidence."
        ar = "ازدادت المخاطر نسبةً إلى الأدلة الفنية الأخيرة."
    else:
        thesis = "Evidence is mixed."
        ar = "الأدلة مختلطة."
    st.write(ar)
    st.caption(thesis)
    st.markdown(f"{s['label_ar']} — اتفاق مؤشرات {s['confidence']:.0f}% — ليست احتمال ربح")
    st.plotly_chart(candle(a["frame"], sym), use_container_width=True)
    fun = fundamentals(sym)
    st.subheader("أساسيات")
    st.caption(f"{fun['source']} • {fun['timestamp']}")
    if fun["available"]:
        st.write({k: display_value(v, pct=k in ("dividend_yield", "revenue_growth", "earnings_growth", "profit_margin", "roe")) for k, v in fun["fields"].items() if k not in ("sector", "industry", "long_name")})
    else:
        st.write("غير متاح — لم تُختلق قيم.")
    chg = a.get("momentum_20")
    st.subheader("أداء تاريخي")
    st.write("زخم 20 جلسة %:", "غير متاح" if chg is None else round(chg, 2))
    st.write("ما يُضعف الأطروحة: كسر مستوى الإبطال", s["levels"].get("invalidation"), "أو تحول الاتجاه الطويل إلى DOWN مع أخبار سلبية موثّقة المصدر.")
    st.subheader("أخبار وأحداث")
    for x in news.search(f"{sym} Egypt earnings", watch)[:8]:
        st.markdown(f"**{x['title']}** ({x['impact']})")
        st.caption(f"{x['source']} • {x['published']}")


def page_portfolio(market):
    st.title("المحفظة • Thndr")
    st.caption("استورد CSV. لا تُطلب كلمة مرور أو OTP أو كوكيز Thndr.")
    cash = float(get_setting("cash_balance", "0") or 0)
    cash = st.number_input("نقد متاح (EGP)", value=cash, min_value=0.0)
    if st.button("حفظ النقد"):
        set_setting("cash_balance", str(cash))
        st.success("حُفظ")
    with st.expander("إضافة عملية"):
        d = st.date_input("التاريخ", date.today())
        sym = st.text_input("السهم").upper()
        side = st.selectbox("النوع", ["BUY", "SELL"])
        qty = st.number_input("الكمية", 1.0)
        price = st.number_input("السعر", 0.0)
        fees = st.number_input("الرسوم", 0.0)
        if st.button("حفظ العملية"):
            portfolio.add_transaction(d.isoformat(), sym, side, qty, price, fees, "manual")
            st.success("حُفظت في SQLite")
    f = st.file_uploader("استيراد CSV من Thndr", type="csv")
    if f and st.button("استيراد إلى قاعدة البيانات"):
        n = portfolio.import_df(pd.read_csv(f), "thndr_csv")
        st.success(f"أُضيف {n} صف")
    tx = portfolio.load_transactions()
    st.dataframe(tx, use_container_width=True, hide_index=True)
    pos = portfolio.positions()
    last_prices = {}
    if not pos.empty:
        for _, r in pos.iterrows():
            h, _ = market.history(r.symbol, "5d")
            last_prices[r.symbol] = float(h.Close.iloc[-1]) if not h.empty else r.avg_cost
    sm = portfolio.summary(last_prices, cash)
    c = st.columns(4)
    c[0].metric("إجمالي المستثمر", f"{sm['total_invested']:,.0f}")
    c[1].metric("قيمة المحفظة", f"{sm['total_portfolio_value']:,.0f}")
    c[2].metric("P/L غير محقق", f"{sm['unrealized_pl']:,.0f}")
    c[3].metric("العائد %", f"{sm['return_pct']:.2f}%")
    st.caption(f"رسوم {sm['total_fees']:,.0f} • محقق {sm['realized_pl']:,.0f} • نقد {sm['available_cash']:,.0f} • يومي: غير متاح بدون إغلاق سابق محفوظ")
    if sm["positions"]:
        st.dataframe(pd.DataFrame(sm["positions"]), use_container_width=True, hide_index=True)


def page_gold(market, news):
    st.title("الذهب")
    df, meta = market.gold_history("1y")
    _meta_caption(meta)
    st.info("هذا مرجع عالمي (عقود/سبوت). سعر الذهب المصري يختلف بالصرف والمصنعية والعرض.")
    if df.empty:
        st.error("تعذر جلب الذهب الدولي.")
    else:
        a = analyze(df)
        s = signal(a)
        st.metric("مرجع دولي", f"{a['last']:.2f}")
        st.write(s["label_ar"], s["disclaimer"])
        st.plotly_chart(candle(a["frame"], "Gold"), use_container_width=True)
    egp, src = market.usd_egp()
    if egp is not None and not egp.empty:
        st.metric("USD/EGP (Yahoo)", f"{float(egp.Close.iloc[-1]):.3f}")
        st.caption(f"المصدر: {src}")
    else:
        st.write("USD/EGP: غير متاح")
    loc, lmeta = market.local_gold_reference()
    st.subheader("مرجع محلي")
    st.caption(str(lmeta))
    if loc:
        st.write(loc)
    for x in news.search("gold الذهب مصر")[:8]:
        st.markdown(f"**{x['title']}** • {x['impact']}")
        st.caption(f"{x['source']} • {x['published']}")


def page_news(news, watch):
    st.title("الأخبار والأحداث")
    q = st.text_input("بحث", "Egypt EGX stocks")
    for x in news.search(q, watch)[:30]:
        st.markdown(f"### {x['title']}")
        st.caption(f"{x['source']} • {x['published']} • {x.get('symbol') or '—'} • {x['impact']}")
        st.write(x.get("summary"))
        st.caption(x.get("impact_note"))
        if x.get("link"):
            st.link_button("فتح الخبر", x["link"])
        st.divider()


def page_briefing(market, news, watch):
    st.title("التقرير اليومي")
    mode = st.radio("النوع", ["قبل الجلسة", "بعد الجلسة"], horizontal=True)
    rows = []
    last_prices = {}
    for sym in watch:
        df, a, s, meta = _load_symbol(market, sym, "1y")
        if a:
            rows.append({"symbol": sym, "analysis": a, "signal": s, "meta": meta})
            last_prices[sym] = a["last"]
    bundle = news.search("EGX البورصة المصرية", watch)[:10]
    cash = float(get_setting("cash_balance", "0") or 0)
    sm = portfolio.summary(last_prices, cash)
    b = briefing(rows, mode, bundle, sm)
    st.markdown(b["text"])
    st.subheader("ترتيب حسب الأدلة")
    st.dataframe(pd.DataFrame(b["table"]), use_container_width=True, hide_index=True)
    st.subheader("أقوى الإعدادات الفنية")
    st.write(b["strong"] or "لا يوجد ضمن العتبة")
    st.subheader("تطورات سلبية فنية")
    st.write(b["weak"] or "لا يوجد ضمن العتبة")
    if mode == "بعد الجلسة":
        st.subheader("المحفظة")
        st.write({k: sm[k] for k in ("total_portfolio_value", "unrealized_pl", "realized_pl", "return_pct")})
    st.subheader("أخبار")
    for n in b["news"]:
        st.write("•", n.get("title"), n.get("impact"))


def page_backtest(market, watch):
    st.title("الاختبار التاريخي")
    st.caption("افتراض رسوم/انزلاق. نتائج الماضي لا تضمن المستقبل.")
    sym = st.selectbox("السهم", watch or ["COMI"])
    strat = st.selectbox("الاستراتيجية", ["sma", "rsi", "macd", "breakout", "trend"])
    fast = st.slider("Fast SMA", 5, 50, 20)
    slow = st.slider("Slow SMA", 30, 200, 50)
    fee = st.number_input("رسوم (bps)", 10.0)
    slip = st.number_input("انزلاق (bps)", 5.0)
    df, meta = market.history(sym, "5y")
    _meta_caption(meta)
    if df.empty:
        st.error("لا توجد بيانات.")
        return
    result = backtest(df, strat, fast, slow, fee_bps=fee, slip_bps=slip)
    c = st.columns(4)
    c[0].metric("العائد", f"{result['return_pct']:.2f}%")
    c[1].metric("Buy & Hold", f"{result['buy_hold_pct']:.2f}%")
    c[2].metric("Max DD", f"{result['max_drawdown_pct']:.2f}%")
    c[3].metric("صفقات", result["trades"])
    c2 = st.columns(4)
    c2[0].metric("CAGR", "غير متاح" if result["cagr"] is None else f"{result['cagr']:.2f}%")
    c2[1].metric("Sharpe", "غير متاح" if result["sharpe"] is None else f"{result['sharpe']:.2f}")
    c2[2].metric("Win %", "غير متاح" if result["win_rate"] is None else f"{result['win_rate']:.1f}%")
    c2[3].metric("Profit factor", "غير متاح" if result["profit_factor"] is None else f"{result['profit_factor']:.2f}")
    st.line_chart(result["equity"].set_index("Date")["equity"])


def page_risk(market, watch):
    st.title("إدارة المخاطر")
    capital = st.number_input("رأس المال", 10000.0)
    risk = st.slider("المخاطرة % للصفة", 0.25, 5.0, 1.0, 0.25)
    max_port = st.slider("حد مخاطر المحفظة %", 1.0, 20.0, 6.0)
    entry = st.number_input("سعر الدخول", 1.0)
    stop = st.number_input("سعر وقف الخسارة", 0.5)
    if entry > stop:
        money = capital * risk / 100
        qty = int(money / (entry - stop)) if entry > stop else 0
        st.metric("الكمية حسب المخاطرة", qty)
        st.metric("قيمة الصفقة", f"{qty * entry:,.2f} EGP")
        st.metric("مسافة الوقف %", f"{(entry - stop) / entry * 100:.2f}%")
        st.caption(f"لا تتجاوز مخاطر مفتوحة مجمّعة حوالي {max_port:.1f}% من رأس المال.")
    cash = float(get_setting("cash_balance", "0") or 0)
    pos = portfolio.positions()
    last = {}
    if not pos.empty:
        for _, r in pos.iterrows():
            h, _ = market.history(r.symbol, "5d")
            last[r.symbol] = float(h.Close.iloc[-1]) if not h.empty else r.avg_cost
    sm = portfolio.summary(last, cash)
    if sm["positions"]:
        exp = pd.DataFrame(sm["positions"])
        tot = exp["value"].sum() or 1
        exp["weight%"] = exp["value"] / tot * 100
        st.subheader("التعرض حسب السهم")
        st.dataframe(exp[["symbol", "quantity", "value", "weight%"]], use_container_width=True, hide_index=True)
        funs = []
        for s in exp["symbol"]:
            f = fundamentals(s)
            sec = f["fields"].get("sector", {})
            funs.append({"symbol": s, "sector": sec.get("value") if sec.get("available") else "غير متاح"})
        st.subheader("القطاع")
        st.dataframe(pd.DataFrame(funs), use_container_width=True, hide_index=True)


def page_alerts(watch):
    st.title("التنبيهات")
    kind = st.selectbox(
        "النوع",
        ["price_above", "price_below", "rsi", "macd_cross", "sma_cross", "breakout", "pct_move", "news_keyword", "favorite_news"],
    )
    sym = st.selectbox("السهم", [""] + (watch or []))
    val = st.number_input("قيمة / عتبة", 0.0)
    kw = st.text_input("كلمة مفتاحية للأخبار")
    if st.button("إنشاء تنبيه"):
        alerts_store.add_alert(kind, sym, {"value": val, "keyword": kw, "op": "above"})
        st.success("حُفظ في SQLite")
    for a in alerts_store.list_alerts():
        cols = st.columns([3, 1, 1])
        cols[0].write(f"{a['id']} • {a['kind']} • {a['symbol']} • {a['params']}")
        if cols[1].button("إيقاف" if a["enabled"] else "تشغيل", key=f"e{a['id']}"):
            alerts_store.set_enabled(a["id"], not a["enabled"])
            st.rerun()
        if cols[2].button("حذف", key=f"d{a['id']}"):
            alerts_store.delete_alert(a["id"])
            st.rerun()


def page_settings(market, news):
    st.title("الإعدادات")
    h = health_check()
    st.write("صحة النظام:", "OK" if h["ok"] else "FAIL")
    st.write("قاعدة البيانات:", h["database"])
    st.write("EGXAPI:", "مُعد" if market.has_api else "Yahoo fallback")
    st.write("News API:", "مُعد" if news.has_api else "RSS")
    theme = st.selectbox("المظهر المحفوظ", ["light", "dark"], index=0 if get_setting("theme", "light") == "light" else 1)
    if st.button("حفظ المظهر"):
        set_setting("theme", theme)
        st.success("حُفظ")
    st.info("أسرار الإنتاج من Streamlit Secrets. لا تعتمد على ملف .env على السحابة.")


def render(page, market, news, watch):
    {
        "لوحة التحكم": lambda: page_dashboard(market, news, watch),
        "السوق": lambda: page_market(market, watch),
        "تحليل سهم": lambda: page_analysis(market, news, watch),
        "السهم المفضل": lambda: page_favorite(market, news, watch),
        "المحفظة": lambda: page_portfolio(market),
        "الذهب": lambda: page_gold(market, news),
        "الأخبار": lambda: page_news(news, watch),
        "التقرير اليومي": lambda: page_briefing(market, news, watch),
        "الاختبار التاريخي": lambda: page_backtest(market, watch),
        "إدارة المخاطر": lambda: page_risk(market, watch),
        "التنبيهات": lambda: page_alerts(watch),
        "الإعدادات": lambda: page_settings(market, news),
    }[page]()
