import logging
from sqlalchemy import create_engine, Column, String, Integer, Boolean, DateTime, MetaData, Table, Float, ForeignKey, select, exists
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from datetime import datetime

from config import settings

logger = logging.getLogger("database")

db_url = settings.DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://')
engine = create_async_engine(db_url, echo=settings.DEBUG)

async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

metadata = MetaData()


dataset_columns = Table(
    "data_processed",
    metadata,
    Column("id", String, primary_key=True),
    Column("dataset_id", String, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False),
    Column("created_at", DateTime, default=datetime.now),
    Column("updated_at", DateTime, default=datetime.now, onupdate=datetime.now),
)

async def init_db():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(metadata.create_all)
            logger.info("Banco de dados inicializado")
    except SQLAlchemyError as e:
        logger.error(f"Erro ao inicializar o banco de dados: {str(e)}")
        raise

async def get_db_session():
    session = async_session()
    try:
        yield session
    finally:
        await session.close()

async def is_dataset_name_unique(name: str) -> bool:
    async with async_session() as session:
        query = select(exists().where(datasets.c.name == name))
        result = await session.execute(query)
        return not result.scalar()
