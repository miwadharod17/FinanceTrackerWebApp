"""
routers/transactions.py
CRUD endpoints for transactions, scoped to the logged-in user via
auth.get_current_user. A user can only ever see/edit/delete their own
transactions — enforced by filtering every query on user_id.
"""

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
import models
import schemas
import auth

router = APIRouter()


@router.post(
    "", response_model=schemas.TransactionOut, status_code=status.HTTP_201_CREATED
)
def create_transaction(
    txn_in: schemas.TransactionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    # If a category_id was passed, make sure it actually exists.
    if txn_in.category_id is not None:
        category = (
            db.query(models.Category)
            .filter(models.Category.id == txn_in.category_id)
            .first()
        )
        if not category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid category_id",
            )

    new_txn = models.Transaction(
        user_id=current_user.id,
        category_id=txn_in.category_id,
        date=txn_in.date,
        description=txn_in.description,
        amount=txn_in.amount,
        type=txn_in.type,
    )
    db.add(new_txn)
    db.commit()
    db.refresh(new_txn)
    return new_txn


@router.get("", response_model=List[schemas.TransactionOut])
def list_transactions(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    type: Optional[schemas.TransactionType] = None,
    category_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """
    Returns the current user's transactions, optionally filtered by
    date range, type (income/expense), or category.
    Powers the dashboard charts — filter server-side rather than pulling
    everything and filtering in the frontend.
    """
    query = db.query(models.Transaction).filter(
        models.Transaction.user_id == current_user.id
    )

    if start_date:
        query = query.filter(models.Transaction.date >= start_date)
    if end_date:
        query = query.filter(models.Transaction.date <= end_date)
    if type:
        query = query.filter(models.Transaction.type == type)
    if category_id:
        query = query.filter(models.Transaction.category_id == category_id)

    return query.order_by(models.Transaction.date.desc()).all()


@router.get("/{transaction_id}", response_model=schemas.TransactionOut)
def get_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    txn = _get_owned_transaction(transaction_id, db, current_user)
    return txn


@router.put("/{transaction_id}", response_model=schemas.TransactionOut)
def update_transaction(
    transaction_id: int,
    txn_in: schemas.TransactionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    txn = _get_owned_transaction(transaction_id, db, current_user)

    txn.date = txn_in.date
    txn.description = txn_in.description
    txn.amount = txn_in.amount
    txn.type = txn_in.type
    txn.category_id = txn_in.category_id

    db.commit()
    db.refresh(txn)
    return txn


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    txn = _get_owned_transaction(transaction_id, db, current_user)
    db.delete(txn)
    db.commit()
    return None


# ---------- Helper ----------

def _get_owned_transaction(
    transaction_id: int, db: Session, current_user: models.User
) -> models.Transaction:
    """
    Fetches a transaction by id, but only if it belongs to the current user.
    Returns 404 (not 403) for transactions owned by someone else, so we
    don't leak which transaction IDs exist.
    """
    txn = (
        db.query(models.Transaction)
        .filter(
            models.Transaction.id == transaction_id,
            models.Transaction.user_id == current_user.id,
        )
        .first()
    )
    if not txn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found"
        )
    return txn