#!/bin/bash
set -e

# Aguardar banco de dados estar disponível
echo "Aguardando banco de dados..."
sleep 5

# Executar migrações
echo "Executando migrações do banco de dados..."
alembic upgrade head

# Iniciar a aplicação
echo "Iniciando a API de Processamento..."
exec uvicorn main:app --host 0.0.0.0 --port 8002