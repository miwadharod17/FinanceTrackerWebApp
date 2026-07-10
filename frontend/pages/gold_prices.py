"""
pages/3_Gold_Prices.py
Live gold price visualization, Kite-app style. Visualization only —
no buy/recommendation logic, per the project requirements.

Uses gold-api.com — free, no API key required, real-time XAU spot price.
"""

from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

from utils import require_login

require_login()

st.set_page_config(page_title="Gold Prices", page_icon="🥇", layout="wide")
st.title("Live Gold Prices")

GOLD_API_URL = "https://api.gold-api.com/price/XAU"

# In-memory price history for this session only (resets on refresh/restart).
# Good enough for a live "ticker" feel without needing a DB table for prices.
if "gold_price_history" not in st.session_state:
    st.session_state.gold_price_history = []


@st.cache_data(ttl=60)
def fetch_gold_price() -> dict | None:
    """
    Cached for 60s so we don't hammer the API on every rerun/interaction.
    Returns None on failure so the UI can show a clear error instead of
    crashing.
    """
    try:
        resp = requests.get(GOLD_API_URL, timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except requests.exceptions.RequestException:
        pass
    return None


data = fetch_gold_price()

if data is None:
    st.error(
        "Couldn't fetch live gold price right now. The API may be temporarily "
        "unavailable — try refreshing in a moment."
    )
else:
    # Field names per gold-api.com's documented response; fall back safely
    # if any are missing rather than crashing the page.
    price = data.get("price")
    symbol = data.get("symbol", "XAU")
    updated_at = data.get("updatedAt", datetime.utcnow().isoformat())

    # Record this reading in session history for the session-level trend line.
    if price is not None:
        st.session_state.gold_price_history.append(
            {"time": datetime.utcnow(), "price": price}
        )
        # Keep history from growing unbounded within a long session.
        st.session_state.gold_price_history = st.session_state.gold_price_history[-200:]

    col1, col2 = st.columns([1, 2])

    with col1:
        st.metric(
            label=f"Gold ({symbol}) — Per Troy Ounce (USD)",
            value=f"${price:,.2f}" if price is not None else "N/A",
        )
        st.caption(f"Last updated: {updated_at}")
        st.caption("Prices refresh automatically every 60 seconds.")

        if st.button("Refresh Now"):
            st.cache_data.clear()
            st.rerun()

    with col2:
        history_df = pd.DataFrame(st.session_state.gold_price_history)
        if len(history_df) >= 2:
            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=history_df["time"],
                    y=history_df["price"],
                    mode="lines+markers",
                    line=dict(color="#D4AF37", width=2),
                    name="Gold Price (USD/oz)",
                )
            )
            fig.update_layout(
                title="Session Price Trend",
                xaxis_title="Time",
                yaxis_title="Price (USD)",
                template="plotly_white",
                height=350,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(
                "Trend chart will appear once a few price readings have been "
                "collected in this session — check back after a couple of refreshes."
            )

st.divider()
st.caption(
    "Live gold prices are shown for informational purposes only. "
    "This page does not provide investment recommendations."
)