"""
main.py
FastAPI entrypoint. Creates DB tables on startup, sets up CORS for the
Streamlit frontend, and mounts all routers.

Auth routes now live in routers/auth_routes.py. Add planned_expenses and
mutual_funds routers the same way once they're built.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_db
from routers import auth_routes, transactions, planned_expenses

# Creates all tables defined in models.py if they don't already exist.
# Fine for SQLite/dev; for production use a migration tool like Alembic instead.
init_db()

app = FastAPI(title="Personal Finance Tracker API")

# Streamlit runs on a different port, so CORS must be enabled.
# Restrict allow_origins to your actual frontend URL in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def health_check():
    return {"status": "ok"}


app.include_router(auth_routes.router, prefix="/auth", tags=["auth"])
app.include_router(transactions.router, prefix="/transactions", tags=["transactions"])
app.include_router(
    planned_expenses.router, prefix="/planned-expenses", tags=["planned-expenses"]
)

# ---------- Other routers (uncomment as you build them) ----------
# from routers import mutual_funds
# app.include_router(mutual_funds.router, prefix="/mutual-funds", tags=["mutual-funds"])