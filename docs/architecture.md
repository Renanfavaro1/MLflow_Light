# Arquitetura do MLflow na Light

O MLflow na Light segue a arquitetura **Remote Tracking with Server** hospedado no GCP.

## Componentes:
1. **Cloud Run (Server)**: Hospeda a UI e a API do MLflow. Configurado com acesso público para as redes permitidas, atuando como único gateway para o backend de metadados e armazenamento.
2. **Cloud SQL (PostgreSQL)**: Armazena os metadados (Runs, Parâmetros, Métricas, Tags). Não possui IP público e é acessado via Serverless VPC Access.
3. **Cloud Storage (GCS)**: Armazena os artefatos pesados (Arquivos `.pkl`, imagens, JSONs).

## Segurança
- O Cloud Run não injeta a senha do banco em texto limpo nas variáveis de ambiente. Ele resolve a connection string diretamente do **Secret Manager**.
- O acesso de rede entre o Cloud Run e o Banco é feito inteiramente por tráfego interno do GCP (VPC).
- Todo o acesso aos recursos do GCP (GCS e Cloud SQL) é abstraído pelo Cloud Run. Os usuários e cientistas de dados interagem com a interface web ou com a API utilizando apenas a URL final, sem necessidade de autenticação (Firebase/IAP) ou contas GCP.
