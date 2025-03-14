# Documentação do Upload API - Analisa.ai

## Visão Geral

O Upload API é um microserviço fundamental da plataforma Analisa.ai, responsável pelo recebimento, processamento inicial e análise exploratória de arquivos de dados dos usuários. Este serviço foi projetado para democratizar o acesso à ciência de dados para PMEs brasileiras, permitindo que usuários sem conhecimento técnico profundo possam iniciar sua jornada de análise de dados.

## Funcionalidades Principais

- **Upload de Arquivos**: Suporte para arquivos CSV, Excel e JSON de até 100 MB.
- **Processamento Automático**: Detecção automática de encoding e delimitadores.
- **Análise Preliminar**: Identificação de problemas comuns nos dados como valores ausentes e desbalanceamento.
- **Sugestões de Tratamento**: Recomendações automáticas para melhorar a qualidade dos dados.
- **Prévia de Dados**: Visualização das primeiras linhas para validação rápida.
- **Conformidade com LGPD**: Opções para exclusão permanente dos dados.

## Arquitetura

O serviço segue uma arquitetura RESTful, construído com FastAPI para alto desempenho e facilidade de documentação. O processamento assíncrono é usado para tarefas intensivas, garantindo boa responsividade da interface mesmo com arquivos grandes.

### Estrutura de Diretórios

```
upload-api/
├── src/
│   ├── __init__.py
│   ├── main.py                  # Ponto de entrada FastAPI
│   ├── config.py                # Configurações do serviço
│   ├── routes/
│   │   ├── __init__.py
│   │   └── upload_routes.py     # Endpoints da API
│   ├── services/
│   │   ├── __init__.py
│   │   ├── file_service.py      # Lógica de processamento de arquivos
│   │   └── validation_service.py # Validação e detecção automática
│   └── models/
│       ├── __init__.py
│       └── file_metadata.py     # Modelos Pydantic
├── Dockerfile
└── requirements.txt
```

## Endpoints da API

### POST `/api/v1/upload`

Recebe um arquivo para processamento.

**Parâmetros:**
- `file`: Arquivo a ser enviado (form-data)
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

### GET `/api/v1/files/{file_id}/preview`

Obtém uma prévia do arquivo carregado.

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

### GET `/api/v1/files/{file_id}/analysis`

Obtém análise detalhada do arquivo carregado.

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

### GET `/api/v1/files`

Lista os arquivos carregados.

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

### DELETE `/api/v1/files/{file_id}`

Remove um arquivo e seus dados processados.

**Parâmetros:**
- `file_id`: ID único do arquivo

**Resposta:**
```json
{
  "message": "Arquivo removido com sucesso",
  "file_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

## Modelos de Dados

### FileMetadata

```python
class FileMetadata(BaseModel):
    id: str
    filename: str
    file_size: int
    upload_date: datetime
    file_type: str  # 'csv', 'xlsx', 'xls', 'json'
    status: str  # 'processing', 'processed', 'error'
    row_count: Optional[int] = None
    column_count: Optional[int] = None
    encoding: Optional[str] = None
    delimiter: Optional[str] = None
    error_message: Optional[str] = None
```

### FilePreview

```python
class FilePreview(BaseModel):
    columns: List[ColumnInfo]
    rows: List[Dict[str, Any]]
    total_rows: int
```

### DataAnalysisResult

```python
class DataAnalysisResult(BaseModel):
    issues: List[DataIssue] = []
    column_stats: Dict[str, Dict[str, Any]] = {}
    row_count: int
    column_count: int
```

## Serviços Principais

### FileService

Responsável pelo gerenciamento do ciclo de vida dos arquivos:
- Salvar arquivos no sistema de arquivos
- Processar e extrair metadados
- Gerar prévias e análises estatísticas
- Gerenciar a exclusão de arquivos

### ValidationService

Especializado na validação e detecção automática:
- Detecção de encoding
- Detecção de delimitadores para CSVs
- Validação da estrutura do arquivo

## Fluxo de Processamento

1. **Upload do Arquivo**: O usuário envia o arquivo através do endpoint `/upload`.
2. **Validação Inicial**: O serviço valida o tamanho e tipo do arquivo.
3. **Detecção Automática**: Se não especificados, o encoding e delimitador são detectados automaticamente.
4. **Processamento Assíncrono**: O arquivo é processado em background para não bloquear a interface.
5. **Análise Exploratória**: São geradas estatísticas, identificados problemas potenciais e sugeridas correções.
6. **Disponibilização**: Os resultados ficam disponíveis para consulta através dos endpoints correspondentes.

## Limites e Restrições

- **Tamanho Máximo**: Arquivos de até 100 MB.
- **Formatos Suportados**: CSV, Excel (.xlsx, .xls) e JSON.
- **Requisitos Mínimos**: Datasets devem ter ao menos 50 linhas para treinamento subsequente.
- **Encoding Padrão**: UTF-8 é usado como fallback quando a detecção falha.

## Integração com Outros Serviços

O Upload API é o ponto de entrada para o fluxo de análise de dados do Analisa.ai e integra-se diretamente com:

- **Training API**: Para iniciar o processo de treinamento com os dados carregados.
- **Gateway API**: Para autenticação e roteamento de requisições.

## Configurações

As principais configurações do serviço podem ser ajustadas através de variáveis de ambiente:

- `DEBUG`: Modo de depuração (padrão: False)
- `PORT`: Porta de execução (padrão: 8001)
- `UPLOAD_FOLDER`: Diretório para armazenamento de arquivos (padrão: "/tmp/analisaai/uploads")
- `MAX_FILE_SIZE`: Tamanho máximo em bytes (padrão: 104857600, equivalente a 100MB)
- `DEFAULT_ENCODING`: Encoding padrão quando não é possível detectar (padrão: "utf-8")

## Instalação e Execução

### Usando Docker

```bash
# Construir a imagem
docker build -t analisaai/upload-api .

# Executar o container
docker run -p 8001:8001 -v /path/to/data:/tmp/analisaai/uploads analisaai/upload-api
```

### Localmente para Desenvolvimento

```bash
# Instalar dependências
pip install -r requirements.txt

# Executar o serviço
cd src
uvicorn main:app --reload --port 8001
```

## Testes

Para executar os testes:

```bash
pytest
```

## Boas Práticas para Uso

- Para arquivos grandes, é recomendado comprimir antes do upload.
- CSVs com encodings específicos (ISO-8859-1, Windows-1252) podem ser explicitamente declarados.
- Verifique a prévia do arquivo logo após o upload para garantir que a detecção automática foi precisa.