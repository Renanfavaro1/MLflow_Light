#!/bin/bash
set -e

unset MLFLOW_AUTH_CONFIG
export MLFLOW_DISABLE_ENV_MANAGER_CHECK=true

# Limita o número de conexões simultâneas que o container faz no Cloud SQL 
export MLFLOW_SQLALCHEMYSTORE_POOL_SIZE=10
export MLFLOW_SQLALCHEMYSTORE_MAX_OVERFLOW=20

echo "Starting MLflow Server with Light Auth plugin..."

exec mlflow server \
    --app-name light-auth \
    --host 0.0.0.0 \
    --port ${PORT:-5000} \
    --backend-store-uri "${BACKEND_STORE_URI}" \
    --default-artifact-root "${DEFAULT_ARTIFACT_ROOT}" \
    --workers 2 \
    --uvicorn-opts "--timeout-keep-alive 120"
