import streamlit as st
from dotenv import load_dotenv

from core.db import init_db
from core.health import check as health_check
from core.market_data import MarketData
from core.news import NewsService
from core.secrets_env import apply_streamlit_secrets
from core.watchlist import add_symbol, list_symbols, remove_symbol
from ui.pages import NAV, render

load_dotenv()
apply_streamlit_secrets()
init_db()

st.set_page_config(page_title="NileQuant", page_icon="📈", layout="wide")
st.markdown(
    """
<style>
.block-container{max-width:1450px;padding-top:1rem}
h1,h2,h3{letter-spacing:-.02em}
</style>
""",
    unsafe_allow_html=True,
)

h = health_check()
if not h["ok"]:
    st.error(f"قاعدة البيانات غير جاهزة: {h['error']}")

market = MarketData()
news = NewsService()

st.sidebar.title("NileQuant")
st.sidebar.caption("EGX • Gold • Intelligence")
page = st.sidebar.radio("القسم", NAV)

st.sidebar.divider()
st.sidebar.subheader("قائمة المتابعة")
add = st.sidebar.text_input("رمز سهم").upper().strip()
if st.sidebar.button("إضافة") and add:
    add_symbol(add)
if st.sidebar.button("حذف الرمز") and add:
    remove_symbol(add)
watch = list_symbols()
st.sidebar.write(" • ".join(watch) if watch else "—")

render(page, market, news, watch)
