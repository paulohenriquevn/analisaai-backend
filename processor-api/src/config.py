import os
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Configurações básicas da aplicação
    APP_NAME: str = "Analisa.ai - Processor API"
    DEBUG: bool = Field(default=False, env="DEBUG")
    PORT: int = Field(default=8002, env="PORT")
    
    # Configurações de armazenamento
    PROCESSED_FOLDER: str = Field(default="/tmp/analisaai/processed", env="PROCESSED_FOLDER")
    UPLOAD_FOLDER: str = Field(default="/tmp/analisaai/uploads", env="UPLOAD_FOLDER")
    
    # Configurações de CORS
    ALLOWED_ORIGINS: list = Field(default=["*"])
    
    # Endpoints de outros serviços
    UPLOAD_API_URL: str = Field(default="http://upload-api:8001", env="UPLOAD_API_URL")
    TRAINING_API_URL: str = Field(default="http://training-api:8003", env="TRAINING_API_URL")
    
    # Configurações para processamento assíncrono
    RABBITMQ_HOST: str = Field(default="rabbitmq", env="RABBITMQ_HOST")
    RABBITMQ_PORT: int = Field(default=5672, env="RABBITMQ_PORT")
    RABBITMQ_USER: str = Field(default="guest", env="RABBITMQ_USER")
    RABBITMQ_PASS: str = Field(default="guest", env="RABBITMQ_PASS")
    
    # Configurações do banco de dados
    DATABASE_URL: str = Field(default="postgresql://analisaai:analisaaiawsedr@localhost:5432/analisaai", env="DATABASE_URL")
    
    # Configurações CAFE
    CAFE_AUTO_VALIDATE: bool = Field(default=True, env="CAFE_AUTO_VALIDATE")
    CAFE_CORRELATION_THRESHOLD: float = Field(default=0.8, env="CAFE_CORRELATION_THRESHOLD")
    CAFE_GENERATE_FEATURES: bool = Field(default=True, env="CAFE_GENERATE_FEATURES")
    CAFE_MAX_PERFORMANCE_DROP: float = Field(default=0.05, env="CAFE_MAX_PERFORMANCE_DROP")
    CAFE_CV_FOLDS: int = Field(default=5, env="CAFE_CV_FOLDS")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Carregar configurações
settings = Settings()

# Garantir que as pastas de processamento existam
os.makedirs(settings.PROCESSED_FOLDER, exist_ok=True)