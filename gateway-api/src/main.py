from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging

from config import settings
from middlewares.auth_middleware import auth_middleware
from middlewares.rate_limiter import rate_limiter_middleware
from routes.upload_routes import router as upload_router
from routes.auth_routes import router as auth_router

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("gateway-api")

# Inicialização da aplicação FastAPI
app = FastAPI(
    title="Analisa.ai - Gateway API",
    description="API Gateway para o ecossistema Analisa.ai",
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

# Aplicar middlewares globais se ativados
if settings.RATE_LIMIT_ENABLED:
    app.middleware("http")(rate_limiter_middleware)

# Inclusão das rotas
app.include_router(auth_router, prefix="/api/auth", tags=["Autenticação"])
app.include_router(upload_router, prefix="/api/upload", tags=["Upload"])
# Outras rotas serão adicionadas conforme os respectivos microserviços sejam desenvolvidos

# Rota de verificação de saúde do serviço
@app.get("/health", tags=["Saúde"])
async def health_check():
    """
    Endpoint para verificação de saúde da API Gateway
    """
    return {"status": "healthy", "service": "gateway-api"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=settings.DEBUG)