# MLflow na Light — Remote Tracking Server no GCP

> **Repositório**: [https://github.com/Renanfavaro1/MLflow_Light.git](https://github.com/Renanfavaro1/MLflow_Light.git)

Implementação corporativa do MLflow na Light utilizando a arquitetura **Remote Tracking with Server**, hospedado no Google Cloud Platform.

O sistema atende a dois cenários principais da Light:
1. **Modelos de ML tradicionais** — treinamento, avaliação, versionamento de modelos (Scikit-Learn, XGBoost, etc.)
2. **Softwares com Foundation Models (GenAI)** — tracking de chamadas a LLMs (Gemini, Vertex AI, OpenAI, Claude), prompts, tokens, latência, custos e árvore hierárquica de Spans (RAGs e Agentes Autônomos).

---

## 🌐 Acesso à Interface Web (Área Light)

O painel visual do MLflow está protegido pelo plugin corporativo de autenticação da Light:

- **URL Oficial**: `https://mlflow-tracking-server-504082412074.us-central1.run.app`
- **Usuário**: `light`
- **Senha**: `Light@2026`

> Ao acessar a URL acima pelo navegador, o pop-up nativo de autenticação solicitará as credenciais corporativas acima.

---

## 🏗️ Estrutura do Repositório

- `infrastructure/`: Configurações Terraform para provisionar Cloud SQL (PostgreSQL), Cloud Storage (GCS), Cloud Run, VPC Peering, IAM e Secret Manager.
- `server/`: Container Docker do MLflow Tracking Server com o plugin nativo de autenticação ASGI/FastAPI (`light-auth`).
- `sdk/`: Pacote Python `light-mlflow` com decoradores (`@track_pipeline`, `@llm_span`, `@tool_span`, `@retriever_span`, `@agent_span`), cálculo de tokens/custos e fail-safe.
- `sdk-node/`: Pacote Node.js/TypeScript `light-mlflow-node` para backends JavaScript (Express, NestJS, etc.).
- `scripts/`: Pipeline ETL de extração otimizada do PostgreSQL para Parquet no GCS (integrado ao Databricks / Unity Catalog).
- `examples/`: Exemplos práticos de uso do SDK para ML e GenAI.
- `docs/`: Manuais completos de setup, arquitetura e instruções para Agentes de IA.

---

## 🔐 Autenticação para Aplicações e Agentes de IA

Para conectar qualquer aplicação, notebook ou Agente de IA ao MLflow da Light, configure as variáveis de ambiente:

| Variável | Descrição | Exemplo |
|---|---|---|
| `MLFLOW_TRACKING_URI` | URL oficial do Tracking Server | `https://mlflow-tracking-server-504082412074.us-central1.run.app` |
| `MLFLOW_TRACKING_TOKEN` | Token corporativo de autenticação | Recuperado do GCP Secret Manager (`mlflow-api-token`) |

> 🛡️ **Arquitetura Dual-Auth & Fail-Safe**:
> - **Agentes de IA e Pipelines**: Utilizam autenticação via Bearer Token (ou Service Account do Cloud Run), passando direto pela API sem bloqueio humano.
> - **Humanos no Navegador**: Acessam a Área Light via Basic Auth (`light` / `Light@2026`).
> - **Resiliência**: Caso o servidor de tracking esteja temporariamente indisponível, as aplicações e Agentes **continuam respondendo normalmente**, sem interrupção de serviço.

---

## 📦 Instalação Rápida dos SDKs

### Python
```bash
pip install git+https://github.com/Renanfavaro1/MLflow_Light.git#subdirectory=sdk
```

### Node.js
```bash
npm install git+https://github.com/Renanfavaro1/MLflow_Light.git#subdirectory=sdk-node
```
