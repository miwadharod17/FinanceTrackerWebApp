"""
pages/1_Dashboard.py
Main dashboard: add/view transactions, spending charts, planned expenses
board, and a redirect button into the Mutual Funds page.
"""

from datetime import date

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

from utils import BACKEND_URL, auth_headers, require_login

require_login()

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
st.title("Dashboard")


# ---------- Data fetch helpers ----------

@st.cache_data(ttl=30)
def fetch_transactions(_headers: dict) -> pd.DataFrame:
    resp = requests.get(f"{BACKEND_URL}/transactions", headers=_headers, timeout=10)
    if resp.status_code != 200:
        return pd.DataFrame()
    df = pd.DataFrame(resp.json())
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df


def fetch_planned_expenses(headers: dict, upcoming_only: bool = True) -> list:
    resp = requests.get(
        f"{BACKEND_URL}/planned-expenses",
        params={"upcoming_only": upcoming_only},
        headers=headers,
        timeout=10,
    )
    return resp.json() if resp.status_code == 200 else []


headers = auth_headers()

# ---------- Add Transaction ----------
with st.expander("Add a transaction", expanded=False):
    with st.form("add_transaction_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            txn_date = st.date_input("Date", value=date.today())
        with col2:
            txn_amount = st.number_input("Amount", min_value=0.01, step=1.0)
        with col3:
            txn_type = st.selectbox("Type", ["expense", "income"])
        txn_desc = st.text_input("Description", placeholder="e.g. Groceries, Salary")

        if st.form_submit_button("Add Transaction"):
            resp = requests.post(
                f"{BACKEND_URL}/transactions",
                json={
                    "date": txn_date.isoformat(),
                    "description": txn_desc,
                    "amount": txn_amount,
                    "type": txn_type,
                },
                headers=headers,
                timeout=10,
            )
            if resp.status_code == 201:
                st.success("Transaction added.")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error(resp.json().get("detail", "Failed to add transaction."))

st.divider()

# ---------- Charts ----------
df = fetch_transactions(headers)

if df.empty:
    st.info("No transactions yet. Add one above to see your charts.")
else:
    total_income = df.loc[df["type"] == "income", "amount"].sum()
    total_expense = df.loc[df["type"] == "expense", "amount"].sum()
    savings_rate = (
        ((total_income - total_expense) / total_income * 100) if total_income > 0 else 0
    )

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Income", f"Rs.{total_income:,.0f}")
    m2.metric("Total Expense", f"Rs.{total_expense:,.0f}")
    m3.metric("Savings Rate", f"{savings_rate:.1f}%")

    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        expense_df = df[df["type"] == "expense"]
        if not expense_df.empty:
            desc_summary = (
                expense_df.groupby("description")["amount"].sum().reset_index()
            )
            fig = px.pie(
                desc_summary,
                names="description",
                values="amount",
                title="Spending Breakdown",
                hole=0.4,
            )
            st.plotly_chart(fig, use_container_width=True)

    with chart_col2:
        trend_df = (
            df.groupby([df["date"].dt.to_period("M").astype(str), "type"])["amount"]
            .sum()
            .reset_index()
        )
        trend_df.columns = ["month", "type", "amount"]
        fig = px.bar(
            trend_df,
            x="month",
            y="amount",
            color="type",
            barmode="group",
            title="Income vs Expense by Month",
        )
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("View all transactions"):
        st.dataframe(
            df[["date", "description", "amount", "type"]].sort_values(
                "date", ascending=False
            ),
            use_container_width=True,
            hide_index=True,
        )

st.divider()

# ---------- Planned Expenses ----------
st.subheader("Upcoming Dues")

planned = fetch_planned_expenses(headers)

with st.expander("Add a planned expense"):
    with st.form("add_planned_expense_form", clear_on_submit=True):
        pe_name = st.text_input("Name", placeholder="e.g. Rent, Electricity Bill")
        pe_amount = st.number_input("Amount", min_value=0.01, step=1.0, key="pe_amount")
        pe_due = st.date_input("Due date", value=date.today(), key="pe_due")

        if st.form_submit_button("Add Planned Expense"):
            resp = requests.post(
                f"{BACKEND_URL}/planned-expenses",
                json={
                    "name": pe_name,
                    "amount": pe_amount,
                    "due_date": pe_due.isoformat(),
                },
                headers=headers,
                timeout=10,
            )
            if resp.status_code == 201:
                st.success("Planned expense added.")
                st.rerun()
            else:
                st.error(resp.json().get("detail", "Failed to add planned expense."))

if not planned:
    st.info("No upcoming dues. Nice and clear!")
else:
    for expense in planned:
        col1, col2, col3 = st.columns([3, 2, 1])
        col1.write(f"{expense['name']}")
        col2.write(f"₹{expense['amount']:,.0f} — due {expense['due_date']}")
        if col3.button("Mark Paid", key=f"paid_{expense['id']}"):
            requests.patch(
                f"{BACKEND_URL}/planned-expenses/{expense['id']}/status",
                json={"status": "paid"},
                headers=headers,
                timeout=10,
            )
            st.rerun()

st.divider()

# ---------- Redirect to Mutual Funds ----------
st.subheader("Looking to invest your savings?")
st.page_link(
    "pages/2_Mutual_Funds.py",
    label="Explore Mutual Fund Schemes & Get a Recommendation",

)