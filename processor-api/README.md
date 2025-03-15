# Documentação da API de Processamento - Analisa.ai

## Visão Geral

A API de Processamento é um componente central da plataforma Analisa.ai, responsável pelo pré-processamento e engenharia de features dos datasets importados. Esta API utiliza exclusivamente a biblioteca CAFE (Component Automated Feature Engineer) para realizar todas as operações de tratamento de dados, garantindo resultados otimizados e consistentes.

## Funcionalidades Principais

- **Tratamento de Valores Ausentes**: Detecção e imputação automática baseada na distribuição dos dados.
- **Detecção e Tratamento de Outliers**: Identificação e tratamento de valores extremos usando diferentes métodos.
- **Normalização e Padronização**: Aplicação de diferentes técnicas de escalonamento como Min-Max e Z-Score.
- **Codificação de Variáveis Categóricas**: Transformação automática usando One-Hot Encoding e Target Encoding.
- **Seleção Automática de Features**: Identificação e seleção das features mais relevantes.
- **Validação de Performance**: Avaliação do impacto das transformações na performance do modelo.

## Arquitetura

A API é construída usando FastAPI e segue uma arquitetura de microserviços. O componente principal é o CAFE, que fornece toda a lógica de processamento.

```
Usuário → Gateway API → Upload API → Processor API (CAFE) → Training API
```

### Estrutura de Diretórios

```
processor-api/
├── src/
│   ├── __init__.py
│   ├── main.py                  # Ponto de entrada FastAPI
│   ├── config.py                # Configurações do serviço
│   ├── alembic/                 # Migrações de banco de dados
│   ├── database/
│   │   ├── __init__.py
│   │   └── db.py                # Conexão com banco de dados
│   ├── models/
│   │   ├── __init__.py
│   │   └── processing_models.py # Modelos de dados
│   ├── routes/
│   │   ├── __init__.py
│   │   └── processor_routes.py  # Endpoints da API
│   └── services/
│       ├── __init__.py
│       └── processor_service.py # Lógica de negócio
├── tests/                       # Testes automatizados
├── Dockerfile
└── requirements.txt
```

## Endpoints da API

### POST `/api/v1/process`

Inicia o processamento de um dataset.

**Corpo da Requisição:**
```json
{
  "dataset_id": "550e8400-e29b-41d4-a716-446655440000",
  "missing_values": {
    "strategy": "auto",
    "categorical_strategy": "most_frequent",
    "numerical_strategy": "mean"
  },
  "outliers": {
    "detection_method": "zscore",
    "treatment_strategy": "clip",
    "z_threshold": 3.0
  },
  "scaling": {
    "method": "minmax"
  },
  "encoding": {
    "method": "auto",
    "max_categories": 10
  },
  "feature_selection": {
    "method": "auto",
    "min_importance": 0.01
  },
  "target_column": "target",
  "columns_to_ignore": ["id", "date"]
}
```

**Resposta:**
```json
{
  "id": "d290f1ee-6c54-4b01-90e6-d701748f0851",
  "dataset_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "created_at": "2025-03-16T14:30:00",
  "updated_at": "2025-03-16T14:30:00",
  "summary": "Processamento iniciado. Use o endpoint /process/{processing_id} para verificar o status."
}
```

### GET `/api/v1/process/{processing_id}`

Obtém o status e resultados de um processamento.

**Resposta:**
```json
{
  "id": "d290f1ee-6c54-4b01-90e6-d701748f0851",
  "dataset_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "created_at": "2025-03-16T14:30:00",
  "updated_at": "2025-03-16T14:35:00",
  "summary": "Processamento concluído com sucesso. 15 transformações aplicadas, 3 colunas com valores ausentes tratados, 2 colunas com outliers tratados.",
  "validation_metrics": {
    "performance_original": 0.85,
    "performance_transformed": 0.89,
    "performance_diff": 0.04,
    "performance_diff_pct": 4.71,
    "feature_reduction": 0.2,
    "original_n_features": 10,
    "transformed_n_features": 8,
    "best_choice": "transformed",
    "metric_used": "accuracy"
  }
}
```

### GET `/api/v1/process/{processing_id}/full`

Obtém detalhes completos do processamento, incluindo todos os relatórios.

### GET `/api/v1/process/{processing_id}/missing-values`

Obtém relatório detalhado de valores ausentes.

### GET `/api/v1/process/{processing_id}/outliers`

Obtém relatório detalhado de outliers detectados e tratados.

### GET `/api/v1/process/{processing_id}/feature-importance`

Obtém relatório de importância das features.

### GET `/api/v1/process/{processing_id}/transformations`

Obtém lista completa de todas as transformações aplicadas.

## Configurações

As principais configurações do serviço podem ser ajustadas através de variáveis de ambiente:

- `DEBUG`: Modo de depuração (padrão: False)
- `PORT`: Porta de execução (padrão: 8002)
- `PROCESSED_FOLDER`: Diretório para armazenamento de arquivos processados
- `DATABASE_URL`: URL de conexão com o banco de dados
- `CAFE_AUTO_VALIDATE`: Ativar validação automática do CAFE (padrão: True)
- `CAFE_CORRELATION_THRESHOLD`: Limiar para remoção de features correlacionadas (padrão: 0.8)
- `CAFE_GENERATE_FEATURES`: Gerar novas features automaticamente (padrão: True)
- `CAFE_MAX_PERFORMANCE_DROP`: Queda máxima de performance permitida (padrão: 0.05)
- `CAFE_CV_FOLDS`: Número de folds para validação cruzada (padrão: 5)

## Instalação e Execução

### Usando Docker

```bash
# Construir a imagem
docker build -t analisaai/processor-api .

# Executar o container
docker run -p 8002:8002 analisaai/processor-api
```

### Localmente para Desenvolvimento

```bash
# Instalar dependências
pip install -r requirements.txt

# Executar migrações do banco de dados
cd src
alembic upgrade head

# Executar o serviço
uvicorn main:app --reload --port 8002
```

## Testes

Para executar os testes:

```bash
pytest
```

## Fluxo de Processamento

1. A API recebe uma solicitação de processamento com configurações específicas.
2. O serviço busca o dataset no serviço de Upload.
3. O CAFE é configurado de acordo com os parâmetros recebidos.
4. O processamento é executado em segundo plano, aplicando:
   - Tratamento de valores ausentes
   - Detecção e tratamento de outliers
   - Normalização/padronização dos dados
   - Codificação de variáveis categóricas
   - Geração de novas features (opcional)
   - Seleção das features mais relevantes
   - Validação de performance
5. Os resultados e relatórios são armazenados no banco de dados.
6. O dataset processado é salvo para uso futuro.

## Integração com CAFE

A API utiliza a biblioteca CAFE para todas as operações de processamento de dados. As principais componentes do CAFE incluem:

- **PreProcessor**: Responsável pelo tratamento de valores ausentes, outliers e normalização.
- **FeatureEngineer**: Responsável pela codificação de variáveis categóricas, geração de novas features e seleção de features.
- **PerformanceValidator**: Responsável por validar o impacto das transformações na performance dos modelos.
- **DataPipeline**: Integra todos os componentes em um único pipeline de processamento.

Para mais detalhes sobre o CAFE, consulte a documentação específica da biblioteca.