# Arquitetura do MLflow na Light

O MLflow na Light segue a arquitetura **Remote Tracking with Server** hospedado no GCP.

## Componentes:
1. **Cloud Run (Server)**: Hospeda a UI e a API do MLflow. Configurado com acesso restrito (internal).
2. **Cloud SQL (PostgreSQL)**: Armazena os metadados (Runs, Parâmetros, Métricas, Tags). Não possui IP público e é acessado via Serverless VPC Access.
3. **Cloud Storage (GCS)**: Armazena os artefatos pesados (Arquivos `.pkl`, imagens, JSONs).
4. **Proxy / Autenticação**: Frontend em React (mesmo padrão do Veritas) que envolve a UI do MLflow e exige login via Firebase Auth antes de permitir acesso.

## Segurança
- O Cloud Run não injeta a senha do banco em texto limpo nas variáveis de ambiente. Ele resolve a connection string diretamente do **Secret Manager**.
- O acesso de rede entre o Cloud Run e o Banco é feito inteiramente por tráfego interno do GCP (VPC).
