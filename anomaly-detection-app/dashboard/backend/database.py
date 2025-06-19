from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.pool import NullPool

from config import DB_URL

# Create async engine for SQLAlchemy
ASYNC_DB_URL = DB_URL.replace('postgresql://', 'postgresql+asyncpg://')
async_engine = create_async_engine(
    ASYNC_DB_URL,
    echo=False,
    poolclass=NullPool,
)

# Create standard engine for synchronous operations
engine = create_engine(DB_URL)

# Create session factories
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    expire_on_commit=False,
    class_=AsyncSession,
)

# Create base model class
Base = declarative_base()
metadata = MetaData()

# Database dependency for FastAPI endpoints
async def get_db():
    async_session = AsyncSessionLocal()
    try:
        yield async_session
    finally:
        await async_session.close()

# Synchronous database session for non-async code
def get_sync_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Async context manager for getting database session
async def get_async_session():
    """Get async database session as context manager"""
    return AsyncSessionLocal()