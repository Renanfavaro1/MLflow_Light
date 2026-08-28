FROM python:3.11-slim

ENV PYTHONUNBUFFERED=True
ENV DATABASE_URL=""
ENV GCS_BUCKET_NAME="mlflow_stats"

WORKDIR /app

# Apenas libpq-dev para psycopg2 (sem build-essential = imagem menor)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements_etl.txt .
RUN pip install --no-cache-dir -r requirements_etl.txt \
    && apt-get purge -y --auto-remove gcc

COPY export_mlflow_to_gcs.py .

CMD ["python", "export_mlflow_to_gcs.py"]
