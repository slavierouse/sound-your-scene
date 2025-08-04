import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from typing import Generator
from dotenv import load_dotenv

# Load environment variables from project root
import os.path as path
project_root = path.dirname(path.dirname(__file__))
env_path = path.join(project_root, '.env')
load_dotenv(env_path, override=True)

# Database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")

# Create engine with robust connection pooling
engine = create_engine(
    DATABASE_URL,
    # Connection pool settings
    pool_size=10,        # Number of connections to maintain in pool
    max_overflow=20,     # Additional connections beyond pool_size
    pool_pre_ping=True,  # Verify connections before use (prevents stale connections)
    pool_recycle=3600,   # Recycle connections after 1 hour (prevents timeout issues)
    
    # Connection timeout settings
    connect_args={
        "connect_timeout": 10,  # Timeout for initial connection
        "application_name": "soundbymood_api"  # Helps identify connections in PostgreSQL logs
    },
    
    # Debugging (set to True during development if needed)
    echo=False
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

def get_db() -> Generator:
    """
    Dependency for getting database session.
    Automatically handles connection pooling - you don't need to manage connections manually.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()  # Returns connection to pool (doesn't actually close it)

def init_db():
    """
    Initialize database tables - SAFE: only creates missing tables.
    Never drops existing tables or data.
    """
    Base.metadata.create_all(bind=engine, checkfirst=True)

def close_db():
    """Clean shutdown of connection pool"""
    engine.dispose()