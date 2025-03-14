from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
import uvicorn
import logging

from config import settings
from routes import upload_routes

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("upload-api")

# Inicialização da aplicação FastAPI
app = FastAPI(
    title="Analisa.ai - API de Upload",
    description="Serviço para upload e processamento inicial de datasets",
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
app.include_router(upload_routes.router, prefix="/api/v1")

# Rota de verificação de saúde do serviço
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "upload-api"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=settings.DEBUG)