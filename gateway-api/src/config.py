import os
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Configurações básicas da aplicação
    APP_NAME: str = "Analisa.ai - Gateway API"
    DEBUG: bool = Field(default=False, env="DEBUG")
    PORT: int = Field(default=8000, env="PORT")
    
    # Configurações de CORS
    ALLOWED_ORIGINS: list = Field(default=["*"])
    
    # URLs dos serviços (microserviços)
    UPLOAD_API_URL: str = Field(default="http://localhost:8001", env="UPLOAD_API_URL")
    TRAINING_API_URL: str = Field(default="http://training-api:8002", env="TRAINING_API_URL")
    EVALUATION_API_URL: str = Field(default="http://evaluation-api:8003", env="EVALUATION_API_URL")
    PREDICTION_API_URL: str = Field(default="http://prediction-api:8004", env="PREDICTION_API_URL")
    
    # Configurações de timeouts (em segundos)
    DEFAULT_TIMEOUT: int = Field(default=30, env="DEFAULT_TIMEOUT")
    
    # Configurações de autenticação
    JWT_SECRET_KEY: str = Field(default="analisaai-secret-key", env="JWT_SECRET_KEY")
    JWT_ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    JWT_EXPIRES_MINUTES: int = Field(default=1440, env="JWT_EXPIRES_MINUTES")  # 24 horas
    
    # Configurações de rate limit
    RATE_LIMIT_ENABLED: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    RATE_LIMIT_REQUESTS: int = Field(default=100, env="RATE_LIMIT_REQUESTS")  # Requisições por janela
    RATE_LIMIT_WINDOW: int = Field(default=60, env="RATE_LIMIT_WINDOW")  # Janela em segundos
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Carregar configurações
settings = Settings()