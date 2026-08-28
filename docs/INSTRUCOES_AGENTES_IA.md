# Integração Light MLflow para Agentes Autônomos

## 📌 Objetivo
Este guia serve como a principal base de conhecimento para o Antigravity (e desenvolvedores de IA) aprenderem a integrar o SDK padrão de Observabilidade da Light (`light_mlflow`) em novos projetos de Agentes de IA, RAGs e orquestradores.

---

## 📦 1. Dependência e Instalação

Ao criar ou atualizar um projeto Python, adicione o pacote ao `requirements.txt`:

```text
# Adicionar no requirements.txt
light-mlflow @ git+https://github.com/Renanfavaro1/MLflow_Light.git#subdirectory=sdk
```

---

## 🔐 2. Autenticação e Configuração de Ambiente

Toda aplicação deve possuir as seguintes variáveis de ambiente configuradas no deploy (Cloud Run, Docker, Kubernetes ou `.env` local):

```bash
# URL do Servidor Central MLflow
MLFLOW_TRACKING_URI="https://mlflow-tracking-server-504082412074.us-central1.run.app"

# Token Corporativo de Acesso (Armazenado no Secret Manager como 'mlflow-api-token')
MLFLOW_TRACKING_TOKEN="28684e077978582afa70be269dbdac57544aae36fb051fa3dc049f2e1c7defd0"
```

No **Cloud Run**, você pode vincular o secret diretamente via flag:
```bash
gcloud run services update NOME_DO_SERVICO \
  --set-env-vars="MLFLOW_TRACKING_URI=https://mlflow-tracking-server-504082412074.us-central1.run.app" \
  --set-secrets="MLFLOW_TRACKING_TOKEN=mlflow-api-token:latest" \
  --region=us-central1
```

> 🛡️ **Resiliência Fail-Safe:** O SDK da Light foi projetado com isolamento de falhas. Se o token não for configurado ou o MLflow estiver temporariamente inacessível, **a aplicação continuará respondendo aos usuários normalmente**, apenas sem gravar os traces.

---

## ⚙️ 3. Inicialização no Código (Startup)

Em todo novo projeto (FastAPI, Flask, scripts ou jobs batch), o MLflow deve ser inicializado **uma única vez** no startup da aplicação, antes de qualquer execução de IA:

```python
from light_mlflow import LightMLflowConfig

# Inicialização limpa: lê URI e TOKEN automaticamente das variáveis de ambiente
LightMLflowConfig.setup(experiment_name="Nome_do_Projeto_Novo")
```

---

## 🔍 4. Rastreamento Nativo (Traces) para Agentes

Para fluxos agenticos e RAGs, utilize **EXCLUSIVAMENTE** a arquitetura de `spans` baseada em decoradores. Isso gera uma árvore visual detalhada (Traces) no painel do MLflow mostrando latência, prompts, respostas, tokens, custos e ferramentas acionadas.

### Importação Padrão:
```python
from light_mlflow.decorators import track_pipeline, agent_span, tool_span, llm_span, retriever_span
```

### Regras Estritas de Aplicação
1. **`@track_pipeline(run_name="...")`**: DEVE ser colocado apenas na **função principal** ou endpoint de entrada (ex: `chat()`, `processar_mensagem()`). Ele é o orquestrador que abre a gravação. Não use `mlflow.start_run()` manualmente.
2. **`@retriever_span(name="...")`**: Obrigatório em funções de busca de contexto (Elasticsearch, Pinecone, bancos vetoriais, buscas SQL para RAG).
3. **`@llm_span(name="...")`**: Obrigatório nas funções que enviam o prompt e recebem a resposta do provedor de IA (Gemini, Vertex AI, OpenAI, Claude). Os tokens e custos são computados automaticamente.
4. **`@tool_span(name="...")`**: Obrigatório em qualquer ferramenta consumida pelo Agente (ex: `consultar_saldo_sap`, `buscar_clima`).
5. **`@agent_span(name="...")`**: Opcional, usado para encapsular loops de raciocínio de agentes ReAct.

### Exemplo Arquitetural Completo:
```python
from light_mlflow.decorators import track_pipeline, tool_span, llm_span, retriever_span

@retriever_span(name="Buscar_Documentos_Normas")
def buscar_normas(query: str):
    # Lógica de busca vetorial / RAG
    return ["Norma 123: Procedimentos de Medição", "Norma 456: Redes"]

@tool_span(name="Consultar_Faturas_SAP")
def buscar_faturas(cpf: str):
    # Integração com API externa
    return f"Faturas abertas para {cpf}: R$ 150,00"

@llm_span(name="Gemini_Gerador_Resposta")
def gerar_resposta_ao_cliente(contexto: str, pergunta: str):
    # Chamada ao SDK do Google Gemini
    return f"Baseado nas informações: {contexto}"

@track_pipeline(run_name="Atendimento_Cliente_Fluxo")
def processar_mensagem(pergunta: str, cpf: str):
    docs = buscar_normas(pergunta)
    faturas = buscar_faturas(cpf)
    contexto = f"{docs}\n{faturas}"
    resposta = gerar_resposta_ao_cliente(contexto, pergunta)
    return resposta
```

---

## 🟢 5. Integração Node.js / TypeScript (Apenas Backend)

Se o projeto for em Node.js (ex: Express, NestJS, Vite SSR), use o pacote `light-mlflow-node`.

### Instalação (package.json):
```json
"dependencies": {
  "light-mlflow-node": "git+https://github.com/Renanfavaro1/MLflow_Light.git#subdirectory=sdk-node"
}
```

### Configuração Inicial (Index.js / Main.js):
```javascript
import { LightMLflowConfig } from 'light-mlflow-node';

// Lê automaticamente MLFLOW_TRACKING_URI e MLFLOW_TRACKING_TOKEN do ambiente
await LightMLflowConfig.setup("Nome_do_Projeto_Node");
```

### Rastreamento de LLMs em Node.js:
```javascript
import { trackPipeline, llmSpan } from 'light-mlflow-node';

const minhaChamadaGemini = llmSpan("Gemini_Resumo", async (texto) => {
    // Integração com o SDK do Google
    return response; 
});

const processarChamada = trackPipeline("Atendimento_Node", async (req) => {
    const dados = await minhaChamadaGemini(req.body.pergunta);
    return dados;
});
```
