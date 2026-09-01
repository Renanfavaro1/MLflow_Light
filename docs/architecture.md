# Arquitetura do MLflow na Light

O MLflow na Light segue a arquitetura **Remote Tracking with Server** hospedado inteiramente no Google Cloud Platform (GCP).

```
                   ┌──────────────────────────────────────┐
                   │           Navegador Web              │
                   │ (Login Light: light / Light@2026)    │
                   └──────────────────┬───────────────────┘
                                      │ Basic Auth
                                      ▼
┌───────────────────────┐      ┌─────────────────────────────┐      ┌─────────────────────────┐
│     Agentes de IA     ├─────►│    Cloud Run (MLflow +      ├─────►│ Cloud SQL (PostgreSQL)  │
│  (Python / Node.js)   │Bearer│       light-auth)           │ VPC  │ (Metadados, Runs,       │
└───────────────────────┘Token └──────────────┬──────────────┘      │  Spans, Traces)         │
                                              │                     └─────────────────────────┘
                                              │ GCS API
                                              ▼
                               ┌─────────────────────────────┐      ┌─────────────────────────┐
                               │     Cloud Storage (GCS)     │◄─────┤ Cloud Run ETL Job       │
                               │ (Artefatos + Exports Parquet├─────►│ (Diário -> Databricks)  │
                               └─────────────────────────────┘      └─────────────────────────┘
```

---

## 🏛️ Componentes Principais

1. **Cloud Run (Tracking Server)**:
   - Hospeda a UI e a API oficial do MLflow (v3.x) em processo único com FastAPI e Uvicorn.
   - Contém o plugin nativo **`light-auth`** registrado via entrypoint `mlflow.app` que implementa o middleware ASGI `LightAuthMiddleware`.
   - Gerencia autenticação dual: **Basic Auth** para acesso humano no browser e **Bearer Tokens** para Agentes/Microsserviços.
   - Conexão segura ao banco de dados via Serverless VPC Access Connector.

2. **Cloud SQL (PostgreSQL)**:
   - Armazena todos os metadados (Experimentos, Runs, Parâmetros, Métricas, Tags, Spans e Traces de GenAI).
   - Sem IP público; acessível exclusivamente via VPC Peering interna da Light.
   - Connection string gerenciada via Google Secret Manager.

3. **Cloud Storage (GCS)**:
   - Bucket `mlflow-artifacts-*`: Armazena artefatos de modelos (`.pkl`, JSONs, imagens, datasets).
   - Bucket `mlflow-stats-*`: Armazena os arquivos Parquet diários extraídos pelo Job de ETL.

4. **Secret Manager**:
   - `mlflow-backend-store-uri`: URI segura de conexão ao PostgreSQL.
   - `mlflow-db-password`: Senha master do usuário do banco.
   - `mlflow-api-token`: Token corporativo compartilhado com os agentes de IA.

5. **Cloud Run Job & Cloud Scheduler (ETL Diário)**:
   - Job automatizado executado diariamente às 03:00 (BRT) que extrai dados do PostgreSQL e gera arquivos Parquet particionados no GCS para consumo pelo Databricks / Unity Catalog.

---

## 🔐 Segurança e Governança

- **Dual-Authentication Transparente**:
  - Usuários humanos visualizam e interagem com a UI do MLflow após login (`light` / `Light@2026`).
  - Agentes de IA utilizam tokens Bearer sem intervenção manual.
  - Endpoints de probe do Cloud Run (`/health`, `/version`) possuem bypass para garantir alta disponibilidade.
- **Rede Fechada**: Tráfego de metadados trafega 100% dentro da VPC interna do Google Cloud.
- **Isolamento de Falhas (Fail-Safe)**: Qualquer instabilidade no tracking server é isolada pelo SDK da Light, garantindo que as aplicações de negócio nunca sejam interrompidas.
