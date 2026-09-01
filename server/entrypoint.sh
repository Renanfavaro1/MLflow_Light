#!/bin/bash
set -e

# Configuração proposital sem autenticação: O acesso já é gerenciado pelo próprio ambiente/rede, facilitando o uso pelo cientista de dados.
unset MLFLOW_AUTH_CONFIG
export MLFLOW_DISABLE_ENV_MANAGER_CHECK=true

# Limita o número de conexões simultâneas que o container faz no Cloud SQL 
# Otimizado para Alta Concorrência (Assistente Virtual)
export MLFLOW_SQLALCHEMYSTORE_POOL_SIZE=10
export MLFLOW_SQLALCHEMYSTORE_MAX_OVERFLOW=20

# As variáveis de ambiente BACKEND_STORE_URI e DEFAULT_ARTIFACT_ROOT
# serão injetadas pelo Cloud Run no momento da execução, utilizando
# Secret Manager e definições da infraestrutura do Terraform.

echo "Starting MLflow Server (Internal on port 5001)..."
echo "Backend Store URI is set."
echo "Default Artifact Root is set to ${DEFAULT_ARTIFACT_ROOT}"

# Roda o MLflow internamente no localhost em background
mlflow server \
    --host 127.0.0.1 \
    --port 5001 \
    --backend-store-uri "${BACKEND_STORE_URI}" \
    --default-artifact-root "${DEFAULT_ARTIFACT_ROOT}" \
    --workers ${MLFLOW_WORKERS:-4} \
    --uvicorn-opts "--timeout-keep-alive 120" &

echo "Starting Light Auth Proxy on port ${PORT:-5000}..."
# Inicia o micro-proxy Flask na frente (porta exposta do Cloud Run)
exec gunicorn -b 0.0.0.0:${PORT:-5000} -w 4 --threads 4 auth_proxy:app
