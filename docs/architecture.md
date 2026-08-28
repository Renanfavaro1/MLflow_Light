# Arquitetura do MLflow na Light

O MLflow na Light segue a arquitetura **Remote Tracking with Server** hospedado inteiramente no GCP.

## Componentes:
1. **Cloud Run (Server)**: Hospeda a UI e a API do MLflow. Atua como o gateway central para o backend de metadados e armazenamento de artefatos.
2. **Cloud SQL (PostgreSQL)**: Armazena os metadados (Runs, Parâmetros, Métricas, Tags, Spans e Traces de GenAI). Não possui IP público e é acessado via Serverless VPC Access.
3. **Cloud Storage (GCS)**: Armazena os artefatos pesados (Arquivos `.pkl`, imagens, JSONs, exports Parquet para o Databricks).
4. **Secret Manager**: Armazena com segurança a connection string do banco de dados e o token corporativo de acesso (`mlflow-api-token`).

## Segurança e Resiliência
- **Autenticação Universal via Token**: Aplicações e notebooks conectam-se via `MLFLOW_TRACKING_TOKEN`, permitindo integração segura a partir do GCP, outras nuvens ou on-premise.
- **VPC Privada**: O tráfego entre o Cloud Run e o Cloud SQL ocorre 100% dentro da VPC interna da Google, sem exposição a IPs públicos de banco de dados.
- **Arquitetura Fail-Safe**: Se o servidor de tracking ou o token falharem, o SDK da Light não interrompe o fluxo de negócios das aplicações e chatbots de IA.
