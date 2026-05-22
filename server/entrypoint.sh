#!/bin/bash
set -e

# As variáveis de ambiente BACKEND_STORE_URI e DEFAULT_ARTIFACT_ROOT
# serão injetadas pelo Cloud Run no momento da execução, utilizando
# Secret Manager e definições da infraestrutura do Terraform.

echo "Starting MLflow Server..."
echo "Backend Store URI is set."
echo "Default Artifact Root is set to ${DEFAULT_ARTIFACT_ROOT}"

mlflow server \
    --host 0.0.0.0 \
    --port 5000 \
    --backend-store-uri "${BACKEND_STORE_URI}" \
    --default-artifact-root "${DEFAULT_ARTIFACT_ROOT}" \
    --workers ${MLFLOW_WORKERS:-2} \
    --gunicorn-opts "--timeout 120"
