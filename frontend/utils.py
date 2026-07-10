"""
utils.py
Shared constants and helpers used by app.py and every page in pages/.

Kept separate from app.py on purpose: app.py has top-level Streamlit UI
code (st.title, st.tabs, forms) that would re-render if another page did
`from app import ...`. Importing from this side-effect-free module avoids
that.
"""

import streamlit as st

BACKEND_URL = "http://localhost:8000"


def auth_headers() -> dict:
    return {"Authorization": f"Bearer {st.session_state.token}"}


def require_login():
    """
    Call at the top of every page in pages/. Stops rendering and shows
    a friendly message if the user isn't logged in, instead of letting
    the page crash on a missing token.
    """
    if "token" not in st.session_state or not st.session_state.token:
        st.warning("Please log in first.")
        st.page_link("app.py", label="Go to Login")
        st.stop()