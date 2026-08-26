FROM python:3.11-slim

# Variáveis de ambiente padrão, podem ser sobrescritas no Cloud Run
ENV PYTHONUNBUFFERED=True
ENV DATABASE_URL=""
ENV GCS_BUCKET_NAME="mlflow_stats"

WORKDIR /app

# Instala as dependências do sistema necessárias para compilar pacotes como o psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copia e instala as dependências Python
COPY requirements_etl.txt .
RUN pip install --no-cache-dir -r requirements_etl.txt

# Copia o script
COPY export_mlflow_to_gcs.py .

# Comando de execução
CMD ["python", "export_mlflow_to_gcs.py"]
