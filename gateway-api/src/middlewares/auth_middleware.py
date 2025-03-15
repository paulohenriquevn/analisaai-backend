from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import logging
from datetime import datetime, timedelta

from config import settings

# Inicialização do logger
logger = logging.getLogger("auth-middleware")

# Instância do bearer token
security = HTTPBearer()

# Lista de rotas públicas que não necessitam de autenticação
PUBLIC_ROUTES = [
    "/health",
    "/api/auth/login",
    "/api/auth/register",
    "/docs",
    "/redoc",
    "/openapi.json"
]

async def auth_middleware(request: Request, call_next):
    """
    Middleware para autenticação JWT
    
    Verifica o token JWT em todas as rotas que não estão na lista de rotas públicas.
    """
    # Verificar se a rota é pública
    path = request.url.path
    if any(path.startswith(route) for route in PUBLIC_ROUTES):
        return await call_next(request)
    
    # Se não for uma rota pública, verificar o token JWT
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticação não fornecido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        scheme, token = auth_header.split()
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Esquema de autenticação inválido",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Verificar o token JWT
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        # Verificar se o token está expirado
        expiration = datetime.fromtimestamp(payload.get("exp", 0))
        if datetime.utcnow() > expiration:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expirado",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Anexar informações do usuário à request para uso nas rotas
        request.state.user = payload.get("sub")
        request.state.user_id = payload.get("user_id")
        request.state.user_role = payload.get("role")
        
        return await call_next(request)
        
    except (JWTError, ValueError) as e:
        logger.error(f"Erro de autenticação: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Erro não esperado no middleware de autenticação: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )