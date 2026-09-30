import os


def apply_streamlit_secrets():
    try:
        import streamlit as st
    except Exception:
        return
    if not hasattr(st, "secrets"):
        return
    keys = (
        "EGXAPI_KEY",
        "EGXAPI_BASE_URL",
        "EGXAPI_ENV",
        "NEWS_API_KEY",
        "LLM_API_KEY",
        "LLM_BASE_URL",
        "LLM_MODEL",
        "GOLD_SYMBOL",
        "LOCAL_GOLD_URL",
        "DATABASE_PATH",
    )
    for k in keys:
        try:
            v = st.secrets.get(k)
            if v:
                os.environ[k] = str(v)
        except Exception:
            pass
