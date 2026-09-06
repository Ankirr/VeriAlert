import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

# Primary PostgreSQL Engine
engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def init_db():
    """Initializes the database schema with automatic fallback resilience."""
    global engine, AsyncSessionLocal
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        target = settings.DATABASE_URL.split("@")[-1] if "@" in settings.DATABASE_URL else settings.DATABASE_URL
        logger.info(f"Database schema initialized successfully on: {target}")
    except Exception as e:
        logger.warning(f"Primary database connection failed ({e}). Activating SQLite fallback...")
        fallback_url = "sqlite+aiosqlite:///./disaster_app.db"
        engine = create_async_engine(fallback_url, echo=False)
        AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database schema initialized with SQLite fallback.")

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
