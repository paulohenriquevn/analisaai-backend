from fastapi import Request, HTTPException, status
import time
import logging
from collections import defaultdict, deque
import asyncio

from config import settings

# Inicialização do logger
logger = logging.getLogger("rate-limiter")

# Dicionário para armazenar as requisições por IP
request_records = defaultdict(lambda: deque(maxlen=500))

# Lock para acesso concorrente aos registros
rate_limit_lock = asyncio.Lock()

# Rotas excluídas do rate limiting
EXCLUDED_ROUTES = [
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json"
]

async def rate_limiter_middleware(request: Request, call_next):
    """
    Middleware para limitação de taxa de requisições (rate limiting)
    
    Limita o número de requisições por IP em uma janela de tempo configurável.
    """
    # Verificar se a rota está excluída do rate limiting
    path = request.url.path
    if any(path.startswith(route) for route in EXCLUDED_ROUTES):
        return await call_next(request)
    
    # Obter o IP do cliente
    client_ip = request.client.host
    current_time = time.time()
    
    async with rate_limit_lock:
        # Remover registros antigos (fora da janela de tempo)
        while request_records[client_ip] and request_records[client_ip][0] < current_time - settings.RATE_LIMIT_WINDOW:
            request_records[client_ip].popleft()
        
        # Verificar se o limite foi excedido
        if len(request_records[client_ip]) >= settings.RATE_LIMIT_REQUESTS:
            logger.warning(f"Rate limit excedido para IP {client_ip} - {len(request_records[client_ip])} requisições")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Limite de requisições excedido. Tente novamente em {settings.RATE_LIMIT_WINDOW} segundos."
            )
        
        # Registrar a requisição atual
        request_records[client_ip].append(current_time)
    
    # Adicionar headers com informações de rate limit
    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(settings.RATE_LIMIT_REQUESTS)
    response.headers["X-RateLimit-Remaining"] = str(settings.RATE_LIMIT_REQUESTS - len(request_records[client_ip]))
    response.headers["X-RateLimit-Reset"] = str(int(current_time + settings.RATE_LIMIT_WINDOW))
    
    return response