# Claude Code Guidelines — Light MLflow Observability

Este repositório e os projetos de IA da Light utilizam o SDK corporativo de Observabilidade e Tracking do MLflow (`light_mlflow`). Ao gerar ou modificar código neste repositório ou em microsserviços de Agentes de IA / RAG da Light, você DEVE seguir rigorosamente as regras abaixo.

---

## 🌐 Credenciais e Acesso (GCP)
- **URL Oficial**: `https://mlflow-tracking-server-504082412074.us-central1.run.app`
- **Ambiente**: Google Cloud Platform (Cloud Run + Cloud SQL + Cloud Storage)
- **Variáveis de Ambiente Obrigatórias**:
  - `MLFLOW_TRACKING_URI`: `"https://mlflow-tracking-server-504082412074.us-central1.run.app"`
  - `MLFLOW_TRACKING_TOKEN`: `"28684e077978582afa70be269dbdac57544aae36fb051fa3dc049f2e1c7defd0"` (no Cloud Run, injetado via Secret Manager como `mlflow-api-token`).

---

## 📦 Dependências

### Python
No `requirements.txt`:
```text
light-mlflow @ git+https://github.com/Renanfavaro1/MLflow_Light.git#subdirectory=sdk
```

### Node.js
No `package.json`:
```json
"dependencies": {
  "light-mlflow-node": "git+https://github.com/Renanfavaro1/MLflow_Light.git#subdirectory=sdk-node"
}
```

---

## ⚙️ Inicialização da Aplicação
Em qualquer script, serviço FastAPI, Flask ou batch job, inicialize **uma única vez** no startup:

```python
from light_mlflow import LightMLflowConfig

# Lê MLFLOW_TRACKING_URI e MLFLOW_TRACKING_TOKEN automaticamente do ambiente
LightMLflowConfig.setup(experiment_name="Nome_do_Projeto")
```

---

## 🔍 Regras Mandatórias de Rastreamento (Spans / Traces)

Para Agentes, fluxos ReAct e pipelines RAG:
1. **Função Orquestradora / Raiz**: Deve SEMPRE ser decorada com `@track_pipeline(run_name="Nome_do_Fluxo")`.
2. **Funções de Inferência LLM**: Deve SEMPRE ser decorada com `@llm_span(name="Nome_do_Passo")`.
   - Compatível nativamente com Anthropic Claude (`anthropic`), Google Gemini (`google-genai` / `vertexai`) e OpenAI (`openai`).
   - Tokens e custos são extraídos e totalizados automaticamente.
3. **Funções de Ferramentas / APIs**: Deve SEMPRE ser decorada com `@tool_span(name="Nome_da_Ferramenta")`.
4. **Funções de Busca Vetorial / RAG**: Deve SEMPRE ser decorada com `@retriever_span(name="Nome_do_Retriever")`.
5. **Loops ReAct / Sub-Agentes**: Use `@agent_span(name="Nome_do_Agente")`.

### 🚨 O que a IA NUNCA deve fazer:
- ❌ **NUNCA** use `mlflow.start_run()` manual em código de Agentes/RAG.
- ❌ **NUNCA** use o decorador legado `@track_llm_call` em agentes (ele não gera a árvore de Spans).
- ❌ **NUNCA** faça hardcode de URLs ou Tokens no código fonte.
- ❌ **NUNCA** levante erros de telemetria para a camada de negócio; o SDK possui mecanismo fail-safe.
- ✅ Suporte completo a funções síncronas (`def`) e assíncronas (`async def`).

---

## 💻 Exemplo de Referência Padrão

```python
from light_mlflow import LightMLflowConfig
from light_mlflow.decorators import track_pipeline, tool_span, llm_span

LightMLflowConfig.setup(experiment_name="Light_Agente_Exemplo")

@tool_span(name="Consultar_Sistema_SAP")
def consultar_sap(id_cliente: str):
    return {"id": id_cliente, "status": "ativo"}

@llm_span(name="Anthropic_Claude_Inferencia")
def chamar_modelo(contexto: dict, mensagem: str):
    # Chamada normal usando qualquer SDK (Anthropic, Gemini, OpenAI)
    return "Resposta processada para o cliente."

@track_pipeline(run_name="Fluxo_Principal_Atendimento")
def processar_atendimento(id_cliente: str, mensagem: str):
    dados = consultar_sap(id_cliente)
    resposta = chamar_modelo(dados, mensagem)
    return resposta
```
