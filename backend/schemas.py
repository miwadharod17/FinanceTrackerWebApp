"""
schemas.py
Pydantic schemas for request validation and response serialization.
Kept separate from models.py (ORM) so API contracts can evolve independently
of the DB schema.
"""

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict


# ---------- Enums (mirror models.py) ----------

class TransactionType(str, Enum):
    income = "income"
    expense = "expense"


class RiskLevel(str, Enum):
    low = "Low"
    medium = "Medium"
    high = "High"


class ExpenseStatus(str, Enum):
    pending = "pending"
    paid = "paid"


# ---------- User / Auth ----------

class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8)


class UserLogin(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    email: EmailStr
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None


# ---------- Category ----------

class CategoryOut(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


# ---------- Transaction ----------

class TransactionCreate(BaseModel):
    date: date
    description: Optional[str] = None
    amount: float = Field(gt=0)
    type: TransactionType
    category_id: Optional[int] = None


class TransactionOut(BaseModel):
    id: int
    date: date
    description: Optional[str]
    amount: float
    type: TransactionType
    category_id: Optional[int]

    model_config = ConfigDict(from_attributes=True)


# ---------- Planned Expense ----------

class PlannedExpenseCreate(BaseModel):
    name: str
    amount: float = Field(gt=0)
    due_date: date
    status: ExpenseStatus = ExpenseStatus.pending


class PlannedExpenseOut(BaseModel):
    id: int
    name: str
    amount: float
    due_date: date
    status: ExpenseStatus

    model_config = ConfigDict(from_attributes=True)


class PlannedExpenseUpdate(BaseModel):
    status: ExpenseStatus


# ---------- Mutual Fund ----------

class MutualFundOut(BaseModel):
    id: int
    scheme_name: str
    amc_name: Optional[str] = None
    fund_manager: Optional[str] = None
    min_sip: Optional[float] = None
    min_lumpsum: Optional[float] = None
    expense_ratio: Optional[float] = None
    fund_size: Optional[float] = None
    fund_age: Optional[float] = None
    category: Optional[str] = None
    sub_category: Optional[str] = None
    rating: Optional[int] = None
    effective_return: Optional[float] = None
    sharpe: Optional[float] = None
    sortino: Optional[float] = None
    risk_level_score: Optional[int] = None
    risk_level: Optional[RiskLevel] = None
    fund_score: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class RecommendRequest(BaseModel):
    monthly_sip_budget: float = Field(gt=0)


# ---------- Recommendation ----------

class RecommendationOut(BaseModel):
    id: int
    fund: MutualFundOut
    risk_bucket: RiskLevel
    recommended_at: datetime

    model_config = ConfigDict(from_attributes=True)