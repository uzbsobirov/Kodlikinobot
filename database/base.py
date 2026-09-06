from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from data import config
import logging

logger = logging.getLogger(__name__)

engine = create_async_engine(
    config.DB_URL,
    echo=False,
    future=True,
    pool_pre_ping=True
)

async_session = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

class Base(DeclarativeBase):
    pass

async def create_tables():
    """Barcha jadvallarni ma'lumotlar bazasida yaratish"""
    import database.models  # Modellar metadataga yuklanishi uchun
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Ma'lumotlar bazasi jadvallari yaratildi yoki yangilandi.")
