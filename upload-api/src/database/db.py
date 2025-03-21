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

datasets = Table(
    "datasets",
    metadata,
    Column("id", String, primary_key=True),
    Column("name", String, unique=True, nullable=False),
    Column("filename", String, nullable=False),
    Column("file_type", String, nullable=False),
    Column("file_size", Integer, nullable=False),
    Column("row_count", Integer),
    Column("column_count", Integer),
    Column("created_at", DateTime, default=datetime.now),
    Column("updated_at", DateTime, default=datetime.now, onupdate=datetime.now),
    Column("status", String, nullable=False),  # 'processed', 'training', 'trained', 'error'
    Column("description", String),
)

dataset_columns = Table(
    "dataset_columns",
    metadata,
    Column("id", String, primary_key=True),
    Column("dataset_id", String, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False),
    Column("name", String, nullable=False),
    Column("data_type", String, nullable=False),
    Column("missing_count", Integer),
    Column("missing_percentage", Float),
    Column("is_target", Boolean, default=False),
    Column("description", String),
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

async def save_dataset(dataset_data: dict) -> dict:
    async with async_session() as session:
        try:
            query = datasets.insert().values(**dataset_data)
            await session.execute(query)
            await session.commit()
            logger.info(f"Dataset {dataset_data['name']} salvo com sucesso")
            return dataset_data
        except SQLAlchemyError as e:
            await session.rollback()
            logger.error(f"Erro ao salvar dataset: {str(e)}")
            raise

async def save_dataset_columns(columns_data: list) -> bool:
    import uuid
    async with async_session() as session:
        try:
            for column_data in columns_data:
                column_data["id"] = str(uuid.uuid4())
                column_data["created_at"] = datetime.now()
                column_data["updated_at"] = datetime.now()
                query = dataset_columns.insert().values(**column_data)
                await session.execute(query)
            
            await session.commit()
            logger.info(f"Colunas do dataset {columns_data[0]['dataset_id']} salvas com sucesso")
            return True
        except SQLAlchemyError as e:
            await session.rollback()
            logger.error(f"Erro ao salvar colunas do dataset: {str(e)}")
            raise