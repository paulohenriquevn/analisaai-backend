# Documentação do Gateway API - Analisa.ai

## Visão Geral

O Gateway API é um componente central da arquitetura do Analisa.ai, atuando como ponto único de entrada para todas as requisições dos clientes. Este serviço redireciona as requisições para os microserviços apropriados, gerencia autenticação, controla taxas de requisição e fornece uma interface unificada para o frontend.

## Características Principais

- **Roteamento de Requisições**: Direciona solicitações para os microserviços correspondentes (upload, treinamento, avaliação, predição)
- **Autenticação Centralizada**: Implementa autenticação JWT para todas as APIs
- **Controle de Taxa (Rate Limiting)**: Protege os serviços contra sobrecarga de requisições
- **Logs Unificados**: Registra todas as solicitações em um formato consistente
- **Tratamento de Erros**: Padroniza respostas de erro em toda a plataforma

## Arquitetura

O Gateway API é construído usando FastAPI, um framework web Python moderno e de alto desempenho, seguindo uma arquitetura de proxy reverso:

```
Cliente Web/Mobile → Gateway API → Microserviços Específicos
                        ↓
                    Autenticação
                    Rate Limiting
                    Logs
```

### Estrutura de Diretórios

```
gateway-api/
├── src/
│   ├── __init__.py
│   ├── main.py                  # Ponto de entrada FastAPI
│   ├── config.py                # Configurações do serviço
│   ├── middlewares/
│   │   ├── __init__.py
│   │   ├── auth_middleware.py   # Middleware de autenticação JWT
│   │   └── rate_limiter.py      # Middleware de controle de taxa
│   └── routes/
│       ├── __init__.py
│       ├── auth_routes.py       # Rotas de autenticação
│       ├── upload_routes.py     # Rotas para o serviço de upload
│       ├── training_routes.py   # Rotas para o serviço de treinamento
│       ├── evaluation_routes.py # Rotas para o serviço de avaliação
│       └── prediction_routes.py # Rotas para o serviço de predição
├── Dockerfile
└── requirements.txt
```

## Endpoints da API

### Autenticação

#### POST `/api/auth/login`

Autentica um usuário e retorna um token JWT.

**Parâmetros (form-data):**
- `username`: Email do usuário
- `password`: Senha do usuário

**Resposta:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

#### POST `/api/auth/register`

Registra um novo usuário e retorna um token JWT.

**Corpo da Requisição:**
```json
{
  "name": "Nome do Usuário",
  "email": "usuario@email.com",
  "password": "senha123"
}
```

**Resposta:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

#### GET `/api/auth/me`

Retorna informações do usuário atual com base no token JWT.

**Cabeçalhos:**
- `Authorization`: Bearer {token}

**Resposta:**
```json
{
  "id": "1",
  "name": "Nome do Usuário",
  "email": "usuario@email.com",
  "role": "user"
}
```

### Upload

#### POST `/api/upload/`

Faz upload de um arquivo para processamento.

**Cabeçalhos:**
- `Authorization`: Bearer {token}

**Parâmetros (form-data):**
- `file`: Arquivo a ser enviado
- `delimiter`: Separador de colunas para CSV (opcional, padrão: ",")
- `encoding`: Encoding do arquivo (opcional, detectado automaticamente se não fornecido)

**Resposta:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "dados_vendas.csv",
  "file_size": 2048576,
  "upload_date": "2025-03-13T14:30:00",
  "file_type": "csv",
  "status": "processing",
  "encoding": "utf-8",
  "delimiter": ","
}
```

#### GET `/api/upload/files/{file_id}/preview`

Obtém uma prévia do arquivo carregado.

**Cabeçalhos:**
- `Authorization`: Bearer {token}

**Parâmetros:**
- `file_id`: ID único do arquivo

**Resposta:**
```json
{
  "columns": [
    {
      "name": "produto",
      "data_type": "object",
      "missing_count": 0,
      "missing_percentage": 0
    },
    {
      "name": "valor",
      "data_type": "float64",
      "missing_count": 5,
      "missing_percentage": 2.5
    }
  ],
  "rows": [
    {"produto": "Monitor", "valor": 1200.50},
    {"produto": "Teclado", "valor": 150.0}
  ],
  "total_rows": 200
}
```

#### GET `/api/upload/files/{file_id}/analysis`

Obtém análise detalhada do arquivo carregado.

**Cabeçalhos:**
- `Authorization`: Bearer {token}

**Parâmetros:**
- `file_id`: ID único do arquivo

**Resposta:**
```json
{
  "issues": [
    {
      "type": "missing_values",
      "description": "A coluna 'valor' contém 5 valores ausentes (2.50%)",
      "severity": "low",
      "column": "valor",
      "suggestion": "Considere remover as linhas com valores ausentes ou preencher com a média/moda"
    }
  ],
  "column_stats": {
    "produto": {
      "unique_values": 40,
      "unique_percentage": 20.0,
      "most_common": "Monitor"
    },
    "valor": {
      "min": 10.5,
      "max": 5000.0,
      "mean": 450.75,
      "median": 320.0,
      "std": 650.3
    }
  },
  "row_count": 200,
  "column_count": 2
}
```

#### GET `/api/upload/files`

Lista os arquivos carregados.

**Cabeçalhos:**
- `Authorization`: Bearer {token}

**Parâmetros:**
- `limit`: Número máximo de arquivos a retornar (padrão: 10)
- `offset`: Deslocamento para paginação (padrão: 0)

**Resposta:**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "filename": "dados_vendas.csv",
    "file_size": 2048576,
    "upload_date": "2025-03-13T14:30:00",
    "file_type": "csv",
    "status": "processed",
    "row_count": 200,
    "column_count": 2,
    "encoding": "utf-8",
    "delimiter": ","
  }
]
```

#### DELETE `/api/upload/files/{file_id}`

Remove um arquivo e seus dados processados.

**Cabeçalhos:**
- `Authorization`: Bearer {token}

**Parâmetros:**
- `file_id`: ID único do arquivo

**Resposta:**
```json
{
  "message": "Arquivo removido com sucesso",
  "file_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

## Configurações

As principais configurações do serviço podem ser ajustadas através de variáveis de ambiente:

| Variável de Ambiente | Descrição | Valor Padrão |
|----------------------|-----------|--------------|
| `PORT` | Porta da aplicação | 8000 |
| `DEBUG` | Modo de depuração | false |
| `ALLOWED_ORIGINS` | Origens permitidas para CORS | ["*"] |
| `UPLOAD_API_URL` | URL do serviço de upload | http://upload-api:8001 |
| `DEFAULT_TIMEOUT` | Timeout padrão para requisições aos serviços (em segundos) | 30 |
| `JWT_SECRET_KEY` | Chave secreta para geração de tokens JWT | analisaai-secret-key |
| `JWT_EXPIRES_MINUTES` | Tempo de expiração do token JWT (em minutos) | 1440 |
| `RATE_LIMIT_ENABLED` | Habilitar limitação de taxa | true |
| `RATE_LIMIT_REQUESTS` | Número máximo de requisições por janela | 100 |
| `RATE_LIMIT_WINDOW` | Janela de tempo para limitação de taxa (em segundos) | 60 |

## Autenticação

O Gateway API implementa autenticação baseada em JWT (JSON Web Tokens). Todas as rotas da API são protegidas, exceto:

- `/health`
- `/api/auth/login`
- `/api/auth/register`
- `/docs`
- `/redoc`
- `/openapi.json`

Para acessar rotas protegidas, os clientes devem:

1. Obter um token JWT via login ou registro
2. Incluir o token no cabeçalho `Authorization` como `Bearer {token}`

### Exemplo de Fluxo de Autenticação

1. **Login**:
   ```bash
   curl -X POST "http://localhost:8000/api/auth/login" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=usuario@email.com&password=senha123"
   ```

2. **Acessar Rota Protegida**:
   ```bash
   curl -X GET "http://localhost:8000/api/upload/files" \
     -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
   ```

## Limitação de Taxa (Rate Limiting)

Para proteger os serviços contra sobrecarga ou ataques de força bruta, o Gateway API implementa limitação de taxa:

- **Janela de Tempo**: 60 segundos (configurável)
- **Requisições Máximas por IP**: 100 por janela (configurável)
- **Resposta em Caso de Excesso**: Status 429 (Too Many Requests)

Os seguintes cabeçalhos são incluídos em cada resposta para informar o cliente sobre o status de limitação:

- `X-RateLimit-Limit`: Número máximo de requisições permitidas
- `X-RateLimit-Remaining`: Requisições restantes na janela atual
- `X-RateLimit-Reset`: Timestamp (em segundos) quando a janela será reiniciada

## Tratamento de Erros

O Gateway API padroniza as respostas de erro em formato JSON:

**Exemplo de Erro 400 (Bad Request)**:
```json
{
  "detail": "Email já está em uso"
}
```

**Exemplo de Erro 401 (Unauthorized)**:
```json
{
  "detail": "Token inválido"
}
```

**Exemplo de Erro 429 (Too Many Requests)**:
```json
{
  "detail": "Limite de requisições excedido. Tente novamente em 60 segundos."
}
```

## Instalação e Execução

### Usando Docker

```bash
# Construir a imagem
docker build -t analisaai/gateway-api .

# Executar o container
docker run -p 8000:8000 analisaai/gateway-api
```

### Usando Docker Compose

```bash
# Iniciar todos os serviços
docker-compose up -d

# Visualizar logs
docker-compose logs -f gateway-api

# Parar os serviços
docker-compose down
```

### Localmente para Desenvolvimento

```bash
# Instalar dependências
pip install -r requirements.txt

# Executar o serviço
cd src
uvicorn main:app --reload --port 8000
```

## Integração com Outros Serviços

O Gateway API é projetado para se integrar com os seguintes microserviços:

1. **Upload API**: Para gerenciamento de datasets
2. **Training API**: Para treinamento de modelos
3. **Evaluation API**: Para avaliação de desempenho de modelos
4. **Prediction API**: Para geração de predições

Conforme esses serviços forem desenvolvidos, novas rotas serão adicionadas ao Gateway API para redirecionamento das requisições.

## Considerações de Segurança

- **Tokens JWT**: Nunca armazene tokens JWT em localStorage. Prefira HTTP-only cookies.
- **Controle de Acesso**: Diferentes papéis de usuário têm diferentes permissões.
- **HTTPS**: Em produção, sempre use HTTPS para proteger as comunicações.
- **Validação de Entrada**: Todas as entradas são validadas antes do processamento.
- **Proteção contra CSRF**: Implemented para endpoints críticos.

## Testes

Para executar os testes:

```bash
pytest
```

## Monitoramento e Logs

O Gateway API registra logs detalhados de todas as requisições, incluindo:

- Timestamp
- Endereço IP do cliente
- Método HTTP
- Endpoint acessado
- Código de status da resposta
- Tempo de resposta

Os logs são enviados para a saída padrão, podendo ser facilmente integrados com ferramentas como ELK Stack ou serviços de APM.