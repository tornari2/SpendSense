"""
Database initialization and connection management.
"""

import os
from pathlib import Path
from sqlalchemy import create_engine, Index
from sqlalchemy.orm import sessionmaker
from spendsense.ingest.schema import Base, Transaction, Account, Recommendation, PersonaHistory


# Database location
DB_DIR = Path(__file__).parent / "data"
DB_PATH = DB_DIR / "spendsense.db"


def get_engine(db_path=None):
    """Get SQLAlchemy engine for database connection."""
    if db_path is None:
        db_path = DB_PATH
    
    # Ensure directory exists
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Create engine with foreign key support
    engine = create_engine(
        f'sqlite:///{db_path}',
        connect_args={'check_same_thread': False},
        echo=False  # Set to True for SQL debugging
    )
    
    # Enable foreign key constraints
    from sqlalchemy import event
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    
    return engine


def get_session(engine=None):
    """Get SQLAlchemy session."""
    if engine is None:
        engine = get_engine()
    
    Session = sessionmaker(bind=engine)
    return Session()


def create_indexes(engine):
    """Create indexes for common query patterns."""
    
    # Transaction indexes
    Index('idx_transactions_account', Transaction.account_id).create(engine, checkfirst=True)
    Index('idx_transactions_date', Transaction.date).create(engine, checkfirst=True)
    Index('idx_transactions_category', Transaction.category_primary).create(engine, checkfirst=True)
    Index('idx_transactions_merchant', Transaction.merchant_name).create(engine, checkfirst=True)
    
    # Account indexes
    Index('idx_accounts_user', Account.user_id).create(engine, checkfirst=True)
    Index('idx_accounts_type', Account.type).create(engine, checkfirst=True)
    
    # Recommendation indexes
    Index('idx_recommendations_user', Recommendation.user_id).create(engine, checkfirst=True)
    Index('idx_recommendations_status', Recommendation.status).create(engine, checkfirst=True)
    Index('idx_recommendations_created', Recommendation.created_at).create(engine, checkfirst=True)
    
    # Persona history indexes
    Index('idx_persona_history_user', PersonaHistory.user_id).create(engine, checkfirst=True)
    Index('idx_persona_history_assigned', PersonaHistory.assigned_at).create(engine, checkfirst=True)


def init_database(db_path=None, drop_existing=False):
    """
    Initialize database schema.
    
    Args:
        db_path: Path to database file (uses default if None)
        drop_existing: If True, drop all tables before creating
    
    Returns:
        SQLAlchemy engine
    """
    engine = get_engine(db_path)
    
    if drop_existing:
        print("Dropping existing tables...")
        Base.metadata.drop_all(engine)
    
    print("Creating database tables...")
    Base.metadata.create_all(engine)
    
    print("Creating indexes...")
    create_indexes(engine)
    
    print(f"Database initialized at: {db_path or DB_PATH}")
    
    return engine


def reset_database():
    """Drop and recreate all tables (useful for development)."""
    return init_database(drop_existing=True)


if __name__ == "__main__":
    # Initialize database when run directly
    init_database(drop_existing=True)
    print("\n✓ Database schema created successfully!")

