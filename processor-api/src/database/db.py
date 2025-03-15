import logging
from sqlalchemy import create_engine, Column, String, Integer, Boolean, DateTime, MetaData, Table, Float, ForeignKey, select, exists, JSON
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

# Tabela para armazenar resultados do processamento
data_processed = Table(
    "data_processed",
    metadata,
    Column("id", String, primary_key=True),
    Column("dataset_id", String, nullable=False),
    Column("preprocessing_config", JSON, nullable=True),
    Column("feature_engineering_config", JSON, nullable=True),
    Column("validation_results", JSON, nullable=True),
    Column("missing_values_report", JSON, nullable=True),
    Column("outliers_report", JSON, nullable=True),
    Column("feature_importance", JSON, nullable=True),
    Column("transformations_applied", JSON, nullable=True),
    Column("transformation_statistics", JSON, nullable=True), 
    Column("best_choice", String, nullable=False, default="original"),  # 'processing', 'completed', 'error'
    Column("status", String, nullable=False),  # 'processing', 'completed', 'error'
    Column("error_message", String, nullable=True),
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

async def save_processing_results(processing_data: dict) -> dict:
    async with async_session() as session:
        try:
            # Verificar se os campos obrigatórios estão presentes
            if 'dataset_id' not in processing_data or 'status' not in processing_data:
                logger.error("Campos obrigatórios missing em save_processing_results: dataset_id, status")
                raise ValueError("Os campos dataset_id e status são obrigatórios")
                
            query = data_processed.insert().values(**processing_data)
            await session.execute(query)
            await session.commit()
            logger.info(f"Resultados de processamento para dataset {processing_data['dataset_id']} salvos com sucesso")
            return processing_data
        except SQLAlchemyError as e:
            await session.rollback()
            logger.error(f"Erro ao salvar resultados de processamento: {str(e)}")
            raise
        
async def update_processing_status(processing_id: str, status: str, error_message: str = None):
    async with async_session() as session:
        try:
            update_dict = {
                "status": status,
                "updated_at": datetime.now()
            }
            
            if error_message:
                update_dict["error_message"] = error_message
                
            query = data_processed.update().where(
                data_processed.c.id == processing_id
            ).values(**update_dict)
            
            await session.execute(query)
            await session.commit()
            logger.info(f"Status de processamento atualizado para {status}: {processing_id}")
            return True
        except SQLAlchemyError as e:
            await session.rollback()
            logger.error(f"Erro ao atualizar status de processamento: {str(e)}")
            raise

async def get_processing_results(processing_id: str):
    async with async_session() as session:
        try:
            query = select(data_processed).where(data_processed.c.id == processing_id)
            result = await session.execute(query)
            record = result.fetchone()
            
            if record:
                return {c.name: getattr(record, c.name) for c in data_processed.columns}
            else:
                return None
        except SQLAlchemyError as e:
            logger.error(f"Erro ao buscar resultados de processamento: {str(e)}")
            raise

async def get_dataset_processing_results(dataset_id: str):
    async with async_session() as session:
        try:
            query = select(data_processed).where(data_processed.c.dataset_id == dataset_id)
            result = await session.execute(query)
            record = result.fetchone()
            
            if record:
                return dict(record)
            else:
                return None
        except SQLAlchemyError as e:
            logger.error(f"Erro ao buscar resultados de processamento para dataset: {str(e)}")
            raise
        
async def update_processing_results(processing_id: str, update_data: dict):
    async with async_session() as session:
        try:
            # Adicionar campo de updated_at automaticamente
            update_data["updated_at"] = datetime.now()
                
            query = data_processed.update().where(
                data_processed.c.id == processing_id
            ).values(**update_data)
            
            await session.execute(query)
            await session.commit()
            logger.info(f"Registro de processamento atualizado: {processing_id}")
            return True
        except SQLAlchemyError as e:
            await session.rollback()
            logger.error(f"Erro ao atualizar registro de processamento: {str(e)}")
            raise