"""
routers/mutual_funds.py
- GET  /mutual-funds            list/filter the fund dataset
- GET  /mutual-funds/{id}       single fund detail
- POST /mutual-funds/recommend  derive a risk profile from the user's own
                                 transaction history and recommend funds

Recommendation logic is intentionally RULE-BASED, not a trained classifier —
see the note in services below. It's a defensible design choice for this
scope; just don't call it "trained ML" in your writeup.
"""

from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
import models
import schemas
import auth

router = APIRouter()


# ---------- Fund listing ----------

@router.get("", response_model=List[schemas.MutualFundOut])
def list_mutual_funds(
    category: Optional[str] = None,
    risk_level: Optional[schemas.RiskLevel] = None,
    max_min_sip: Optional[float] = None,
    sort_by_score: bool = True,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """
    Powers the Mutual Funds dashboard table. Filterable by category,
    risk bucket, and affordability (max_min_sip). Sorted by fund_score
    (best funds first) unless sort_by_score=False.
    """
    query = db.query(models.MutualFund)

    if category:
        query = query.filter(models.MutualFund.category == category)
    if risk_level:
        query = query.filter(models.MutualFund.risk_level == risk_level)
    if max_min_sip is not None:
        query = query.filter(models.MutualFund.min_sip <= max_min_sip)

    if sort_by_score:
        query = query.order_by(models.MutualFund.fund_score.desc())

    return query.limit(limit).all()


@router.get("/categories", response_model=List[str])
def list_categories(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Distinct categories, for populating a filter dropdown in the frontend."""
    rows = db.query(models.MutualFund.category).distinct().all()
    return sorted({r[0] for r in rows if r[0]})


@router.get("/{fund_id}", response_model=schemas.MutualFundOut)
def get_mutual_fund(
    fund_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    fund = db.query(models.MutualFund).filter(models.MutualFund.id == fund_id).first()
    if not fund:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fund not found")
    return fund


# ---------- Recommendation ----------

# Numeric risk_level ceiling (SEBI riskometer scale, 1-6) allowed per bucket.
# e.g. a user profiled as "Medium" can be shown funds with risk_level_score <= 4.
RISK_BUCKET_CEILING = {
    "Low": 2,
    "Medium": 4,
    "High": 6,
}


def _profile_user_risk(db: Session, user_id: int) -> str:
    """
    Derives a risk bucket (Low/Medium/High) from the user's own transaction
    history over the last 6 months. Rule-based, not ML — three simple,
    explainable signals:

      1. Savings rate = (income - expense) / income
         Higher savings rate => more room to absorb volatility => more risk.
      2. Expense volatility = std dev of monthly expense totals
         Higher volatility => less predictable cash flow => less risk.
      3. Income regularity = number of distinct months with income logged
         Sparse/irregular income => be conservative by default.

    If there isn't enough transaction history yet, defaults to "Low" —
    the safe choice when we don't have enough signal.
    """
    six_months_ago = date.today() - timedelta(days=180)
    txns = (
        db.query(models.Transaction)
        .filter(
            models.Transaction.user_id == user_id,
            models.Transaction.date >= six_months_ago,
        )
        .all()
    )

    if len(txns) < 5:
        return "Low"

    total_income = sum(t.amount for t in txns if t.type == models.TransactionType.income)
    total_expense = sum(t.amount for t in txns if t.type == models.TransactionType.expense)

    if total_income <= 0:
        return "Low"

    savings_rate = (total_income - total_expense) / total_income

    # Monthly expense totals, for a simple volatility proxy (std / mean).
    monthly_expense: dict = {}
    for t in txns:
        if t.type != models.TransactionType.expense:
            continue
        key = (t.date.year, t.date.month)
        monthly_expense[key] = monthly_expense.get(key, 0) + t.amount

    values = list(monthly_expense.values())
    if len(values) >= 2:
        mean_exp = sum(values) / len(values)
        variance = sum((v - mean_exp) ** 2 for v in values) / len(values)
        std_exp = variance ** 0.5
        volatility_ratio = (std_exp / mean_exp) if mean_exp > 0 else 1.0
    else:
        volatility_ratio = 1.0  # not enough months to judge; be conservative

    income_months = len({(t.date.year, t.date.month) for t in txns if t.type == models.TransactionType.income})

    # ----- Decision rules -----
    if savings_rate >= 0.30 and volatility_ratio < 0.4 and income_months >= 3:
        return "High"
    elif savings_rate >= 0.10 and volatility_ratio < 0.7:
        return "Medium"
    return "Low"


@router.post("/recommend", response_model=List[schemas.MutualFundOut])
def recommend_funds(
    request: schemas.RecommendRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """
    Only called when the user explicitly clicks "Recommend" — never
    automatic. Profiles the user's risk bucket from their transaction
    history, then filters+ranks funds by:
      - min_sip <= the SIP budget the user entered
      - risk_level_score <= the ceiling for their risk bucket
      - ordered by fund_score (highest first)
    Logs the top pick to the recommendations table for history.
    """
    risk_bucket = _profile_user_risk(db, current_user.id)
    risk_ceiling = RISK_BUCKET_CEILING[risk_bucket]

    eligible = (
        db.query(models.MutualFund)
        .filter(
            models.MutualFund.min_sip <= request.monthly_sip_budget,
            models.MutualFund.risk_level_score <= risk_ceiling,
        )
        .order_by(models.MutualFund.fund_score.desc())
        .limit(5)
        .all()
    )

    if not eligible:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "No funds match your budget and risk profile. Try increasing "
                "your SIP budget."
            ),
        )

    # Log the top recommendation for history / "past recommendations" feature.
    top_fund = eligible[0]
    log_entry = models.Recommendation(
        user_id=current_user.id,
        fund_id=top_fund.id,
        risk_bucket=risk_bucket,
    )
    db.add(log_entry)
    db.commit()

    return eligible