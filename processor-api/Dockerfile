FROM python:3.10-slim

# Metadados da imagem
LABEL maintainer="Analisa.ai Team <contato@analisa.ai>"
LABEL description="Processor API para a plataforma Analisa.ai"
LABEL version="0.1.0"

# Evitar geração de arquivos .pyc
ENV PYTHONDONTWRITEBYTECODE=1
# Garantir que a saída do Python seja enviada diretamente para o terminal sem buffering
ENV PYTHONUNBUFFERED=1
# Definir o diretório de trabalho dentro do container
WORKDIR /app

# Instalar dependências necessárias para compilação de algumas bibliotecas
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements.txt primeiro para aproveitar o cache do Docker
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar o código da aplicação
COPY src/ .

# Criar diretório para armazenar dados processados
RUN mkdir -p /data/processed && \
    chmod 777 /data/processed

# Configurar variáveis de ambiente padrão
ENV PORT=8002
ENV PROCESSED_FOLDER=/data/processed
ENV DEBUG=false

# Expor a porta da aplicação
EXPOSE ${PORT}

# Copiar script de inicialização
COPY start.sh .
RUN chmod +x start.sh

# Comando para executar a aplicação
CMD ["./start.sh"]

# Verificação de saúde
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:${PORT}/health || exit 1