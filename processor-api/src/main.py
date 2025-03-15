from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging

from config import settings
from routes import processor_routes
from database.db import init_db

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("processor-api")

# Inicialização da aplicação FastAPI
app = FastAPI(
    title="Analisa.ai - API de Processamento",
    description="Serviço para processamento avançado de datasets utilizando CAFE",
    version="0.1.0",
)

# Configuração de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclusão das rotas
app.include_router(processor_routes.router, prefix="/api/v1")

# Eventos de inicialização e encerramento
@app.on_event("startup")
async def startup_event():
    logger.info("Inicializando a API de Processamento...")
    await init_db()
    logger.info("API de Processamento inicializada")

# Rota de verificação de saúde do serviço
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "processor-api"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=settings.DEBUG)