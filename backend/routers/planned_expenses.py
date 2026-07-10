"""
routers/planned_expenses.py
CRUD endpoints for planned/upcoming expenses (rent due, bills due, etc.),
scoped to the logged-in user. Powers the "upcoming dues" board on the
dashboard.
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
    "", response_model=schemas.PlannedExpenseOut, status_code=status.HTTP_201_CREATED
)
def create_planned_expense(
    expense_in: schemas.PlannedExpenseCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    new_expense = models.PlannedExpense(
        user_id=current_user.id,
        name=expense_in.name,
        amount=expense_in.amount,
        due_date=expense_in.due_date,
        status=expense_in.status,
    )
    db.add(new_expense)
    db.commit()
    db.refresh(new_expense)
    return new_expense


@router.get("", response_model=List[schemas.PlannedExpenseOut])
def list_planned_expenses(
    status_filter: Optional[schemas.ExpenseStatus] = None,
    upcoming_only: bool = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """
    Returns the current user's planned expenses.
    - status_filter: 'pending' or 'paid'
    - upcoming_only: if true, only returns expenses with due_date >= today
    Ordered by due_date ascending so the nearest due item shows first —
    matches how a "bills due" board should read.
    """
    query = db.query(models.PlannedExpense).filter(
        models.PlannedExpense.user_id == current_user.id
    )

    if status_filter:
        query = query.filter(models.PlannedExpense.status == status_filter)
    if upcoming_only:
        query = query.filter(models.PlannedExpense.due_date >= date.today())

    return query.order_by(models.PlannedExpense.due_date.asc()).all()


@router.get("/{expense_id}", response_model=schemas.PlannedExpenseOut)
def get_planned_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    return _get_owned_expense(expense_id, db, current_user)


@router.put("/{expense_id}", response_model=schemas.PlannedExpenseOut)
def update_planned_expense(
    expense_id: int,
    expense_in: schemas.PlannedExpenseCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    expense = _get_owned_expense(expense_id, db, current_user)

    expense.name = expense_in.name
    expense.amount = expense_in.amount
    expense.due_date = expense_in.due_date
    expense.status = expense_in.status

    db.commit()
    db.refresh(expense)
    return expense


@router.patch("/{expense_id}/status", response_model=schemas.PlannedExpenseOut)
def update_planned_expense_status(
    expense_id: int,
    status_in: schemas.PlannedExpenseUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """
    Lightweight endpoint just for toggling paid/pending — e.g. a checkbox
    on the dashboard — without needing to resend the full expense object.
    """
    expense = _get_owned_expense(expense_id, db, current_user)
    expense.status = status_in.status
    db.commit()
    db.refresh(expense)
    return expense


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_planned_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    expense = _get_owned_expense(expense_id, db, current_user)
    db.delete(expense)
    db.commit()
    return None


# ---------- Helper ----------

def _get_owned_expense(
    expense_id: int, db: Session, current_user: models.User
) -> models.PlannedExpense:
    """
    Fetches a planned expense by id, but only if it belongs to the current
    user. Returns 404 (not 403) for expenses owned by someone else.
    """
    expense = (
        db.query(models.PlannedExpense)
        .filter(
            models.PlannedExpense.id == expense_id,
            models.PlannedExpense.user_id == current_user.id,
        )
        .first()
    )
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Planned expense not found"
        )
    return expense