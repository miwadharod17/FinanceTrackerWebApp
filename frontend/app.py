"""
app.py
Streamlit entrypoint. Handles login/signup and stores the JWT in
st.session_state. Other pages (Dashboard, Mutual Funds, Gold Prices) live
in pages/ and each check st.session_state for a valid token before
rendering — see the auth guard snippet in the docstring of each page.
"""

import requests
import streamlit as st

from utils import BACKEND_URL, auth_headers

st.set_page_config(page_title="Personal Finance Tracker", page_icon="🏦", layout="wide")


# ---------- Session state defaults ----------
if "token" not in st.session_state:
    st.session_state.token = None
if "username" not in st.session_state:
    st.session_state.username = None


# ---------- Already logged in ----------
if st.session_state.token:
    st.title(f"Welcome back, {st.session_state.username}")
    st.write("Use the sidebar to navigate to your Dashboard, Mutual Funds, or Gold Prices.")

    if st.button("Log out"):
        st.session_state.token = None
        st.session_state.username = None
        st.rerun()

    st.stop()


# ---------- Login / Signup ----------
st.title("Personal Finance Tracker")

login_tab, signup_tab = st.tabs(["Log In", "Sign Up"])

with login_tab:
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log In")

        if submitted:
            if not username or not password:
                st.error("Please enter both username and password.")
            else:
                try:
                    resp = requests.post(
                        f"{BACKEND_URL}/auth/login",
                        json={"username": username, "password": password},
                        timeout=10,
                    )
                except requests.exceptions.ConnectionError:
                    st.error("Can't reach the backend. Is the FastAPI server running?")
                else:
                    if resp.status_code == 200:
                        st.session_state.token = resp.json()["access_token"]
                        st.session_state.username = username
                        st.success("Logged in!")
                        st.rerun()
                    else:
                        detail = resp.json().get("detail", "Login failed.")
                        st.error(detail)

with signup_tab:
    with st.form("signup_form"):
        new_username = st.text_input("Choose a username")
        new_email = st.text_input("Email")
        new_password = st.text_input(
            "Choose a password", type="password", help="Minimum 8 characters"
        )
        signup_submitted = st.form_submit_button("Sign Up")

        if signup_submitted:
            if not new_username or not new_email or not new_password:
                st.error("Please fill in all fields.")
            elif len(new_password) < 8:
                st.error("Password must be at least 8 characters.")
            else:
                try:
                    resp = requests.post(
                        f"{BACKEND_URL}/auth/signup",
                        json={
                            "username": new_username,
                            "email": new_email,
                            "password": new_password,
                        },
                        timeout=10,
                    )
                except requests.exceptions.ConnectionError:
                    st.error("Can't reach the backend. Is the FastAPI server running?")
                else:
                    if resp.status_code == 201:
                        st.success("Account created! Please log in from the Log In tab.")
                    else:
                        detail = resp.json().get("detail", "Signup failed.")
                        st.error(detail)