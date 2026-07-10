"""
pages/2_Mutual_Funds.py
- Always: browsable/filterable mutual fund dataset table.
- Only on request: user enters their monthly SIP budget, clicks
  "Get My Recommendation", and the backend profiles their risk bucket
  from their own transaction history and returns matching funds.
Nothing is recommended automatically — matches the project requirement.
"""

import pandas as pd
import requests
import streamlit as st

from utils import BACKEND_URL, auth_headers, require_login

require_login()

st.set_page_config(page_title="Mutual Funds", page_icon="📈", layout="wide")
st.title("Mutual Funds")

headers = auth_headers()


# ---------- Data fetch helpers ----------

@st.cache_data(ttl=300)
def fetch_categories(_headers: dict) -> list:
    resp = requests.get(f"{BACKEND_URL}/mutual-funds/categories", headers=_headers, timeout=10)
    return resp.json() if resp.status_code == 200 else []


@st.cache_data(ttl=60)
def fetch_funds(_headers: dict, category: str, risk_level: str, max_min_sip: float) -> pd.DataFrame:
    params = {"limit": 100}
    if category != "All":
        params["category"] = category
    if risk_level != "All":
        params["risk_level"] = risk_level
    if max_min_sip:
        params["max_min_sip"] = max_min_sip

    resp = requests.get(f"{BACKEND_URL}/mutual-funds", params=params, headers=_headers, timeout=10)
    return pd.DataFrame(resp.json()) if resp.status_code == 200 else pd.DataFrame()


# ---------- Fund dataset browser ----------

st.subheader("Browse Available Schemes")

filter_col1, filter_col2, filter_col3 = st.columns(3)
with filter_col1:
    categories = ["All"] + fetch_categories(headers)
    selected_category = st.selectbox("Category", categories)
with filter_col2:
    selected_risk = st.selectbox("Risk Level", ["All", "Low", "Medium", "High"])
with filter_col3:
    max_sip_filter = st.number_input(
        "Max min. SIP (₹)", min_value=0, value=0, step=100,
        help="0 = no filter",
    )

funds_df = fetch_funds(headers, selected_category, selected_risk, max_sip_filter or None)

if funds_df.empty:
    st.info("No funds match these filters. Try widening your search.")
else:
    display_cols = [
        "scheme_name", "category", "risk_level", "rating",
        "effective_return", "expense_ratio", "min_sip", "fund_score",
    ]
    display_cols = [c for c in display_cols if c in funds_df.columns]
    st.dataframe(
        funds_df[display_cols].rename(columns={
            "scheme_name": "Scheme",
            "category": "Category",
            "risk_level": "Risk",
            "rating": "Rating",
            "effective_return": "Return %",
            "expense_ratio": "Expense Ratio %",
            "min_sip": "Min SIP (₹)",
            "fund_score": "Score",
        }),
        use_container_width=True,
        hide_index=True,
    )
    st.caption(f"Showing {len(funds_df)} funds, ranked by composite score.")

st.divider()

# ---------- Recommendation (on request only) ----------

st.subheader("Get a Personalized Recommendation")
st.write(
    "We'll look at your recent transaction history — savings rate, spending "
    "stability, and income regularity — to work out a risk profile, then "
    "match it against your SIP budget."
)

with st.form("recommend_form"):
    monthly_sip = st.number_input(
        "How much can you invest monthly? (₹)",
        min_value=100,
        value=1000,
        step=100,
        help="This is required — we filter funds by their minimum SIP against this amount.",
    )
    get_recommendation = st.form_submit_button("Get My Recommendation", type="primary")

if get_recommendation:
    if monthly_sip < 100:
        st.error("Please enter a valid monthly SIP amount (minimum ₹100).")
    else:
        with st.spinner("Analyzing your transaction history..."):
            resp = requests.post(
                f"{BACKEND_URL}/mutual-funds/recommend",
                json={"monthly_sip_budget": monthly_sip},
                headers=headers,
                timeout=15,
            )

        if resp.status_code == 200:
            recommendations = resp.json()
            st.success(f"Based on your profile, here are your top {len(recommendations)} matches:")

            for fund in recommendations:
                with st.container(border=True):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**{fund['scheme_name']}**")
                        st.caption(
                            f"{fund.get('category', 'N/A')} • "
                            f"{fund.get('sub_category', '')}"
                        )
                    with col2:
                        st.metric("Risk", fund.get("risk_level", "N/A"))

                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Return", f"{fund.get('effective_return', 0):.1f}%")
                    m2.metric("Expense Ratio", f"{fund.get('expense_ratio', 0):.2f}%")
                    m3.metric("Min SIP", f"₹{fund.get('min_sip', 0):,.0f}")
                    m4.metric("Rating", f"{fund.get('rating', 'N/A')} ")

        elif resp.status_code == 404:
            st.warning(resp.json().get("detail", "No matching funds found."))
            st.info(
                "Tip: try increasing your monthly SIP budget, or add a few more "
                "transactions on your Dashboard so we can better assess your "
                "spending pattern."
            )
        else:
            st.error("Something went wrong fetching your recommendation. Please try again.")