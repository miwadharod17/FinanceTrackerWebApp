"""
models.py
SQLAlchemy ORM models matching the normalized schema:
users, categories, transactions, planned_expenses, mutual_funds, recommendations
"""

import enum
from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Date,
    DateTime,
    ForeignKey,
    Enum,
    Index,
)
from sqlalchemy.orm import relationship

from database import Base


class TransactionType(str, enum.Enum):
    income = "income"
    expense = "expense"


class RiskLevel(str, enum.Enum):
    low = "Low"
    medium = "Medium"
    high = "High"


class ExpenseStatus(str, enum.Enum):
    pending = "pending"
    paid = "paid"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    transactions = relationship(
        "Transaction", back_populates="user", cascade="all, delete-orphan"
    )
    planned_expenses = relationship(
        "PlannedExpense", back_populates="user", cascade="all, delete-orphan"
    )
    recommendations = relationship(
        "Recommendation", back_populates="user", cascade="all, delete-orphan"
    )


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)  # Food, Rent, Salary, etc.

    transactions = relationship("Transaction", back_populates="category")


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        Index("ix_transactions_user_id_date", "user_id", "date"),
        Index("ix_transactions_user_id_type_date", "user_id", "type", "date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    date = Column(Date, nullable=False, default=datetime.utcnow)
    description = Column(String, nullable=True)
    amount = Column(Float, nullable=False)
    type = Column(Enum(TransactionType), nullable=False)

    user = relationship("User", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")


class PlannedExpense(Base):
    __tablename__ = "planned_expenses"
    __table_args__ = (
        Index(
            "ix_planned_expenses_user_id_due_date_status",
            "user_id",
            "due_date",
            "status",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)  # "Rent", "Electricity Bill"
    amount = Column(Float, nullable=False)
    due_date = Column(Date, nullable=False)
    status = Column(Enum(ExpenseStatus), default=ExpenseStatus.pending)

    user = relationship("User", back_populates="planned_expenses")


class MutualFund(Base):
    __tablename__ = "mutual_funds"
    __table_args__ = (
        Index(
            "ix_mutual_funds_category_risk_level",
            "category",
            "risk_level",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    scheme_name = Column(String, nullable=False)
    amc_name = Column(String, nullable=True)
    fund_manager = Column(String, nullable=True)
    min_sip = Column(Float, nullable=True)
    min_lumpsum = Column(Float, nullable=True)
    expense_ratio = Column(Float, nullable=True)
    fund_size = Column(Float, nullable=True)
    fund_age = Column(Float, nullable=True)
    category = Column(String, nullable=True)  # Equity / Debt / Hybrid / Other
    sub_category = Column(String, nullable=True)
    rating = Column(Integer, nullable=True)  # 0-5 star rating
    effective_return = Column(Float, nullable=True)  # best available of 1/3/5yr returns
    sharpe = Column(Float, nullable=True)
    sortino = Column(Float, nullable=True)
    risk_level_score = Column(Integer, nullable=True)  # raw 1-6 SEBI riskometer scale
    risk_level = Column(Enum(RiskLevel), nullable=True)  # bucketed Low/Medium/High
    fund_score = Column(Float, nullable=True)  # weighted composite score, used for ranking

    recommendations = relationship("Recommendation", back_populates="fund")


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    fund_id = Column(Integer, ForeignKey("mutual_funds.id"), nullable=False)
    risk_bucket = Column(Enum(RiskLevel), nullable=False)
    recommended_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="recommendations")
    fund = relationship("MutualFund", back_populates="recommendations")