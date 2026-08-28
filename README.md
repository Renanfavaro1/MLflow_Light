# MLflow na Light — Remote Tracking Server no GCP

> **Repositório**: [https://github.com/Renanfavaro1/MLflow_Light.git](https://github.com/Renanfavaro1/MLflow_Light.git)

Implementação corporativa do MLflow na Light utilizando a arquitetura **Remote Tracking with Server**, hospedado no Google Cloud Platform.

O sistema atende a dois cenários principais da Light:
1. **Modelos de ML tradicionais** — treinamento, avaliação, versionamento de modelos (Scikit-Learn, XGBoost, etc.)
2. **Softwares com Foundation Models (GenAI)** — tracking de chamadas a LLMs (Gemini, Vertex AI, OpenAI, Claude), prompts, tokens, latência, custos e árvore hierárquica de Spans (RAGs e Agentes Autônomos).

---

## 🏗️ Estrutura do Repositório

- `infrastructure/`: Configurações Terraform para provisionar Cloud SQL, Cloud Storage, Cloud Run, VPC, IAM e Secret Manager.
- `server/`: Container Docker customizado para rodar o MLflow Tracking Server conectado aos serviços GCP.
- `sdk/`: Pacote Python `light-mlflow` contendo decoradores (`@track_pipeline`, `@llm_span`, `@tool_span`), cálculo automático de tokens/custos e resiliência fail-safe.
- `sdk-node/`: Pacote Node.js/TypeScript `light-mlflow-node` para backends JavaScript (Express, NestJS, etc.).
- `scripts/`: Pipeline ETL de extração otimizada do PostgreSQL para Parquet no GCS (integrado ao Databricks / Unity Catalog).
- `examples/`: Exemplos práticos de uso do SDK para ML e GenAI.
- `docs/`: Guias detalhados de setup, arquitetura e integração para Agentes de IA.

---

## 🔐 Autenticação & Variáveis de Ambiente

Para conectar qualquer aplicação ou notebook ao MLflow da Light, defina as variáveis de ambiente:

| Variável | Descrição | Exemplo |
|---|---|---|
| `MLFLOW_TRACKING_URI` | URL oficial do Tracking Server | `https://mlflow-tracking-server-504082412074.us-central1.run.app` |
| `MLFLOW_TRACKING_TOKEN` | Token corporativo de autenticação | Recuperado do GCP Secret Manager (`mlflow-api-token`) |

> 🛡️ **Arquitetura Fail-Safe**: Caso o token não seja fornecido ou o servidor de tracking esteja inacessível, as aplicações e Agentes de IA **continuam funcionando normalmente**. A telemetria nunca interrompe a resposta ao usuário final.

---

## 📦 Instalação Rápida

### Python
```bash
pip install git+https://github.com/Renanfavaro1/MLflow_Light.git#subdirectory=sdk
```

### Node.js
```bash
npm install git+https://github.com/Renanfavaro1/MLflow_Light.git#subdirectory=sdk-node
```
