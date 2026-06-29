#!/bin/bash
set -e

# Configuração proposital sem autenticação: O acesso já é gerenciado pelo próprio ambiente/rede, facilitando o uso pelo cientista de dados.
unset MLFLOW_AUTH_CONFIG
export MLFLOW_DISABLE_ENV_MANAGER_CHECK=true

# Limita o número de conexões simultâneas que o container faz no Cloud SQL 
# para não estourar o limite (FATAL: remaining connection slots...)
export MLFLOW_SQLALCHEMYSTORE_POOL_SIZE=2
export MLFLOW_SQLALCHEMYSTORE_MAX_OVERFLOW=3

# As variáveis de ambiente BACKEND_STORE_URI e DEFAULT_ARTIFACT_ROOT
# serão injetadas pelo Cloud Run no momento da execução, utilizando
# Secret Manager e definições da infraestrutura do Terraform.

echo "Starting MLflow Server..."
echo "Backend Store URI is set."
echo "Default Artifact Root is set to ${DEFAULT_ARTIFACT_ROOT}"

mlflow server \
    --host 0.0.0.0 \
    --port ${PORT:-5000} \
    --backend-store-uri "${BACKEND_STORE_URI}" \
    --default-artifact-root "${DEFAULT_ARTIFACT_ROOT}" \
    --workers ${MLFLOW_WORKERS:-2} \
    --uvicorn-opts "--timeout-keep-alive 120"
