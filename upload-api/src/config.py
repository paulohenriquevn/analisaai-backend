import os
from pydantic import BaseSettings, Field

class Settings(BaseSettings):
    # Configurações básicas da aplicação
    APP_NAME: str = "Analisa.ai - Upload API"
    DEBUG: bool = Field(default=False, env="DEBUG")
    PORT: int = Field(default=8001, env="PORT")
    
    # Configurações de armazenamento
    UPLOAD_FOLDER: str = Field(default="/tmp/analisaai/uploads", env="UPLOAD_FOLDER")
    MAX_FILE_SIZE: int = Field(default=104857600, env="MAX_FILE_SIZE")  # 100MB em bytes
    
    # Configurações de CORS
    ALLOWED_ORIGINS: list = Field(default=["*"])
    
    # Endpoints de outros serviços
    TRAINING_API_URL: str = Field(default="http://training-api:8002", env="TRAINING_API_URL")
    
    # Configurações para processamento assíncrono
    RABBITMQ_HOST: str = Field(default="rabbitmq", env="RABBITMQ_HOST")
    RABBITMQ_PORT: int = Field(default=5672, env="RABBITMQ_PORT")
    RABBITMQ_USER: str = Field(default="guest", env="RABBITMQ_USER")
    RABBITMQ_PASS: str = Field(default="guest", env="RABBITMQ_PASS")
    
    # Tipos de arquivos suportados
    SUPPORTED_FILE_TYPES: List[str] = Field(default=["csv", "xlsx", "xls", "json"])
    
    # Configurações de encoding
    DEFAULT_ENCODING: str = Field(default="utf-8", env="DEFAULT_ENCODING")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Carregar configurações
settings = Settings()

# Garantir que as pastas de upload existam
os.makedirs(settings.UPLOAD_FOLDER, exist_ok=True)