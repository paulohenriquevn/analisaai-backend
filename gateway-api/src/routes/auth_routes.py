from fastapi import APIRouter, HTTPException, Depends, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt, JWTError
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import logging
import uuid

from config import settings

# Inicialização do logger
logger = logging.getLogger("auth-routes")

# Inicialização do router
router = APIRouter()

# Esquema OAuth2 para autenticação
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# Modelos de dados
class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    user_id: Optional[str] = None
    exp: Optional[int] = None
    role: Optional[str] = None

# Usuários fictícios para o MVP
# Em produção, seria substituído por um banco de dados
USERS_DB = {
    "admin@analisaai.com": {
        "id": "1",
        "name": "Admin",
        "email": "admin@analisaai.com",
        "password": "admin123",  # Em produção, seria armazenado como hash
        "role": "admin"
    },
    "user@analisaai.com": {
        "id": "2",
        "name": "Usuário Demo",
        "email": "user@analisaai.com",
        "password": "user123",  # Em produção, seria armazenado como hash
        "role": "user"
    }
}

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Cria um token JWT com os dados fornecidos
    
    Args:
        data: Dados a serem codificados no token
        expires_delta: Tempo de expiração do token
        
    Returns:
        Token JWT codificado
    """
    to_encode = data.copy()
    
    # Definir tempo de expiração
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRES_MINUTES)
    
    # Adicionar claim de expiração
    to_encode.update({"exp": expire})
    
    # Codificar token
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.JWT_SECRET_KEY, 
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Endpoint para autenticação e obtenção de token JWT
    
    Args:
        form_data: Formulário com email e senha
        
    Returns:
        Token JWT
    """
    # Verificar se o usuário existe
    user = USERS_DB.get(form_data.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verificar a senha (em produção, seria verificado o hash)
    if user["password"] != form_data.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Criar token JWT
    access_token = create_access_token(
        data={
            "sub": user["email"],
            "user_id": user["id"],
            "role": user["role"]
        }
    )
    
    # Retornar token
    return Token(access_token=access_token)

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister):
    """
    Endpoint para registro de novos usuários
    
    Args:
        user_data: Dados do novo usuário
        
    Returns:
        Token JWT para o novo usuário
    """
    # Verificar se o email já está em uso
    if user_data.email in USERS_DB:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email já está em uso"
        )
    
    # Gerar ID único para o novo usuário
    user_id = str(uuid.uuid4())
    
    # Armazenar usuário (em produção, seria em um banco de dados com senha hash)
    USERS_DB[user_data.email] = {
        "id": user_id,
        "name": user_data.name,
        "email": user_data.email,
        "password": user_data.password,  # Em produção, seria armazenado como hash
        "role": "user"  # Papel padrão para novos usuários
    }
    
    # Criar token JWT
    access_token = create_access_token(
        data={
            "sub": user_data.email,
            "user_id": user_id,
            "role": "user"
        }
    )
    
    # Retornar token
    return Token(access_token=access_token)

@router.get("/me")
async def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Endpoint para obter informações do usuário atual
    
    Args:
        token: Token JWT
        
    Returns:
        Informações do usuário atual
    """
    try:
        # Decodificar token
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        # Extrair email
        email = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Verificar se o usuário existe
        user = USERS_DB.get(email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuário não encontrado",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Retornar informações do usuário (exceto senha)
        return {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"]
        }
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )