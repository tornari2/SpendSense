"""
Database schema definitions for SpendSense.
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, 
    ForeignKey, Text, Date, JSON
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class User(Base):
    """User table - synthetic users with consent tracking."""
    __tablename__ = 'users'
    
    user_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    credit_score = Column(Integer, nullable=True)  # Synthetic credit score (300-850)
    consent_status = Column(Boolean, default=False, nullable=False)
    consent_timestamp = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    accounts = relationship("Account", back_populates="user", cascade="all, delete-orphan")
    consent_logs = relationship("ConsentLog", back_populates="user", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="user", cascade="all, delete-orphan")
    persona_history = relationship("PersonaHistory", back_populates="user", cascade="all, delete-orphan")


class Account(Base):
    """Account table - checking, savings, credit cards, etc."""
    __tablename__ = 'accounts'
    
    account_id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('users.user_id'), nullable=False)
    type = Column(String, nullable=False)  # checking, savings, credit_card, money_market, hsa
    subtype = Column(String, nullable=True)
    balance_available = Column(Float, nullable=True)
    balance_current = Column(Float, nullable=False)
    credit_limit = Column(Float, nullable=True)  # For credit cards
    iso_currency_code = Column(String, default='USD', nullable=False)
    holder_category = Column(String, default='personal', nullable=False)  # Exclude business
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account", cascade="all, delete-orphan")
    liabilities = relationship("Liability", back_populates="account", cascade="all, delete-orphan")


class Transaction(Base):
    """Transaction table - all financial transactions."""
    __tablename__ = 'transactions'
    
    transaction_id = Column(String, primary_key=True)
    account_id = Column(String, ForeignKey('accounts.account_id'), nullable=False)
    date = Column(Date, nullable=False)
    amount = Column(Float, nullable=False)  # Positive = debit, Negative = credit/income
    merchant_name = Column(String, nullable=True)
    merchant_entity_id = Column(String, nullable=True)
    payment_channel = Column(String, nullable=True)  # online, in store, other
    category_primary = Column(String, nullable=False)
    category_detailed = Column(String, nullable=True)
    pending = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    account = relationship("Account", back_populates="transactions")


class Liability(Base):
    """Liability table - credit card debt, loans, mortgages."""
    __tablename__ = 'liabilities'
    
    liability_id = Column(String, primary_key=True)
    account_id = Column(String, ForeignKey('accounts.account_id'), nullable=False)
    type = Column(String, nullable=False)  # credit_card, mortgage, student_loan
    apr_percentage = Column(Float, nullable=True)
    apr_type = Column(String, nullable=True)  # fixed, variable
    minimum_payment_amount = Column(Float, nullable=True)
    last_payment_amount = Column(Float, nullable=True)
    is_overdue = Column(Boolean, default=False, nullable=False)
    next_payment_due_date = Column(Date, nullable=True)
    last_statement_balance = Column(Float, nullable=True)
    interest_rate = Column(Float, nullable=True)  # For loans
    
    # Relationships
    account = relationship("Account", back_populates="liabilities")


class ConsentLog(Base):
    """Consent log - track consent changes over time."""
    __tablename__ = 'consent_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey('users.user_id'), nullable=False)
    consent_status = Column(Boolean, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    source = Column(String, nullable=True)  # API, operator, system
    notes = Column(Text, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="consent_logs")


class Recommendation(Base):
    """Recommendation table - store generated recommendations."""
    __tablename__ = 'recommendations'
    
    recommendation_id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('users.user_id'), nullable=False)
    recommendation_type = Column(String, nullable=False)  # education, offer
    content = Column(Text, nullable=False)
    rationale = Column(Text, nullable=False)  # Plain-language explanation
    persona = Column(String, nullable=True)  # Associated persona
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(String, default='pending', nullable=False)  # pending, approved, rejected, sent
    operator_notes = Column(Text, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="recommendations")
    decision_trace = relationship("DecisionTrace", back_populates="recommendation", uselist=False, cascade="all, delete-orphan")


class DecisionTrace(Base):
    """Decision trace - auditability for recommendations."""
    __tablename__ = 'decision_traces'
    
    trace_id = Column(String, primary_key=True)
    recommendation_id = Column(String, ForeignKey('recommendations.recommendation_id'), nullable=False)
    input_signals = Column(JSON, nullable=False)  # All signals used
    triggered_signals = Column(JSON, nullable=True)  # List of signal IDs that triggered this recommendation
    signal_context = Column(JSON, nullable=True)  # Signal-specific context data
    persona_assigned = Column(String, nullable=True)
    persona_reasoning = Column(Text, nullable=True)
    template_used = Column(String, nullable=True)
    variables_inserted = Column(JSON, nullable=True)
    variable_sources = Column(JSON, nullable=True)  # Source of each variable (where it came from)
    eligibility_checks = Column(JSON, nullable=True)
    base_data = Column(JSON, nullable=True)  # Base data (transactions, accounts, liabilities) used to derive signals
    rationale_variables = Column(JSON, nullable=True)  # Variables used in rationale generation
    rationale_variable_sources = Column(JSON, nullable=True)  # Sources of rationale variables
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    version = Column(String, default='1.0', nullable=False)
    
    # Relationships
    recommendation = relationship("Recommendation", back_populates="decision_trace")


class PersonaHistory(Base):
    """Persona history - track persona assignments over time."""
    __tablename__ = 'persona_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey('users.user_id'), nullable=False)
    persona = Column(String, nullable=False)
    window_days = Column(Integer, nullable=False)  # 30 or 180
    assigned_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    signals = Column(JSON, nullable=True)  # Key signals that triggered assignment
    
    # Relationships
    user = relationship("User", back_populates="persona_history")

