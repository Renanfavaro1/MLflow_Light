# Integração Light MLflow para Agentes Autônomos & Claude Code

## 📌 Objetivo
Este guia é o padrão corporativo da Light para observabilidade de Agentes de IA, fluxos RAG e orquestradores utilizando o SDK `light_mlflow`.
Ele foi formatado para ser consumido tanto por desenvolvedores humanos quanto por assistentes de código autônomos, especialmente o **Claude Code** (Anthropic) e o **Antigravity**.

> 💡 **Para quem usa o Claude Code:**
> Para que o Claude Code siga automaticamente essas regras em qualquer projeto de IA na Light, basta **copiar este arquivo como `CLAUDE.md` na raiz do repositório do seu projeto** (ou usar o arquivo pronto `CLAUDE.md`). O Claude Code o carregará como diretriz do sistema em todas as sessões.

---

## 🌐 Acesso ao Painel Visual (Área Light)

Para visualizar os experimentos, métricas e a árvore de rastreamento (Traces) dos seus agentes:
- **URL**: `https://mlflow-tracking-server-504082412074.us-central1.run.app`
- **Usuário**: `light`
- **Senha**: `Light@2026`

---

## 📦 1. Dependência e Instalação

Adicione o SDK corporativo ao arquivo de dependências do projeto:

### Python (`requirements.txt`):
```text
light-mlflow @ git+https://github.com/Renanfavaro1/MLflow_Light.git#subdirectory=sdk
```

Instalação local via terminal:
```bash
pip install git+https://github.com/Renanfavaro1/MLflow_Light.git#subdirectory=sdk
```

### Node.js / TypeScript (`package.json`):
```json
"dependencies": {
  "light-mlflow-node": "git+https://github.com/Renanfavaro1/MLflow_Light.git#subdirectory=sdk-node"
}
```

---

## 🔐 2. Autenticação e Configuração de Ambiente

Toda aplicação instrumentada deve ter as duas variáveis de ambiente configuradas no runtime (Cloud Run, Docker, Kubernetes ou `.env` local):

```bash
# URL oficial do Servidor Central MLflow no GCP
MLFLOW_TRACKING_URI="https://mlflow-tracking-server-504082412074.us-central1.run.app"

# Token corporativo de acesso (disponível no GCP Secret Manager como 'mlflow-api-token')
MLFLOW_TRACKING_TOKEN="28684e077978582afa70be269dbdac57544aae36fb051fa3dc049f2e1c7defd0"
```

### No Google Cloud Run:
```bash
gcloud run services update NOME_DO_SERVICO \
  --set-env-vars="MLFLOW_TRACKING_URI=https://mlflow-tracking-server-504082412074.us-central1.run.app" \
  --set-secrets="MLFLOW_TRACKING_TOKEN=mlflow-api-token:latest" \
  --region=us-central1
```

> 🛡️ **Resiliência Fail-Safe:** O SDK da Light foi projetado com isolamento de falhas. Se o token não for configurado ou o MLflow estiver temporariamente inacessível, **a aplicação continuará respondendo aos usuários normalmente**, sem travar nem lançar exceções.

---

## ⚙️ 3. Inicialização no Código (Startup)

Em todo novo projeto (FastAPI, Flask, scripts ou jobs batch), o MLflow deve ser inicializado **uma única vez** no startup da aplicação, antes de qualquer chamada de IA:

```python
from light_mlflow import LightMLflowConfig

# Inicialização limpa: lê URI e TOKEN automaticamente das variáveis de ambiente
LightMLflowConfig.setup(experiment_name="Nome_do_Seu_Projeto")
```

---

## 🔍 4. Rastreamento Nativo (Traces) para Agentes e RAGs

Para fluxos agenticos e RAGs, utilize **EXCLUSIVAMENTE** a arquitetura de `spans` baseada em decoradores. Isso gera uma árvore visual detalhada (Traces) no painel do MLflow exibindo latência, prompts, respostas, contagem de tokens, custos em dólar e chamadas a ferramentas.

### Importação Padrão:
```python
from light_mlflow.decorators import track_pipeline, agent_span, tool_span, llm_span, retriever_span
```

### Regras Estritas de Aplicação (Mandatórias para o Claude Code):
1. **`@track_pipeline(run_name="...")`**: DEVE ser colocado **apenas na função orquestradora principal** ou endpoint de entrada (ex: `chat()`, `processar_mensagem()`). Ele é o nó raiz que abre o Trace. **Nunca use `mlflow.start_run()` manualmente.**
2. **`@retriever_span(name="...")`**: Obrigatório em funções de recuperação de contexto (Elasticsearch, Pinecone, ChromaDB, buscas vetoriais ou consultas SQL para RAG).
3. **`@llm_span(name="...")`**: Obrigatório em funções que fazem a chamada de inferência à LLM (Anthropic Claude, Google Gemini, Vertex AI, OpenAI). Os tokens e custos são calculados automaticamente.
4. **`@tool_span(name="...")`**: Obrigatório em qualquer ferramenta ou API consumida pelo Agente (ex: consultar saldo SAP, emitir 2ª via, consultar clima).
5. **`@agent_span(name="...")`**: Opcional, usado para encapsular sub-agentes ou loops de raciocínio ReAct dentro da pipeline principal.

---

## 🚨 5. Diretrizes Críticas para Assistentes de IA (Claude Code / Antigravity)

Quando o Claude Code ou outra IA estiver gerando código para a Light:
- ❌ **NUNCA use `@track_llm_call`** em fluxos de Agentes ou RAGs: esse decorador legado cria runs isoladas e não gera a árvore hierárquica na aba Traces.
- ❌ **NUNCA use `mlflow.start_run()` manual**: deixe o `@track_pipeline` gerenciar o ciclo de vida do trace.
- ❌ **NUNCA faça hardcode de credenciais**: não insira URLs ou Tokens diretamente no código Python; deixe a leitura automática via `LightMLflowConfig.setup(...)`.
- ❌ **NUNCA interrompa o fluxo de negócio com erros de telemetria**: todas as exceções do MLflow são isoladas pelo SDK. Suas funções de negócio devem tratar apenas seus próprios erros de domínio.
- ✅ **Suporte total a funções síncronas e assíncronas**: todos os decoradores suportam tanto `def` quanto `async def`.

---

## 💻 6. Exemplos Arquiteturais Prontos

### Exemplo A: Agente com Anthropic Claude SDK (`anthropic`)
```python
import anthropic
from light_mlflow import LightMLflowConfig
from light_mlflow.decorators import track_pipeline, tool_span, llm_span

# 1. Setup no startup
LightMLflowConfig.setup(experiment_name="Light_Agente_Claude")

client = anthropic.Anthropic()

@tool_span(name="Consultar_Fatura_SAP")
def consultar_fatura_sap(cpf: str):
    # Simula consulta à API externa
    return {"cpf": cpf, "status": "aberta", "valor": 184.50, "vencimento": "10/11/2026"}

@llm_span(name="Claude_Gerador_Resposta")
def chamar_claude(prompt: str, contexto: dict):
    # Chamada ao SDK oficial da Anthropic (Tokens e custos computados automaticamente)
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        messages=[
            {"role": "user", "content": f"Contexto do cliente: {contexto}\n\nPergunta: {prompt}"}
        ]
    )
    return response.content[0].text

@track_pipeline(run_name="Atendimento_Fatura_Cliente")
def processar_atendimento(pergunta: str, cpf: str):
    dados_fatura = consultar_fatura_sap(cpf)
    resposta = chamar_claude(pergunta, dados_fatura)
    return resposta

if __name__ == "__main__":
    resultado = processar_atendimento("Qual o valor da minha fatura?", "123.456.789-00")
    print(resultado)
```

---

### Exemplo B: Pipeline RAG com Google Gemini SDK e Busca Vetorial
```python
from google import genai
from light_mlflow import LightMLflowConfig
from light_mlflow.decorators import track_pipeline, retriever_span, llm_span

LightMLflowConfig.setup(experiment_name="Light_RAG_Normas_Tecnicas")

gemini_client = genai.Client()

@retriever_span(name="Buscar_Base_Vetorial")
def buscar_normas(query: str):
    # Simula busca no banco vetorial / Elasticsearch
    return [
        "Norma NTD-001: Padrão de Entrada Residencial",
        "Norma NTD-015: Instalação de Transformadores em Poste"
    ]

@llm_span(name="Gemini_Sintese")
def gerar_resposta_gemini(normas: list, pergunta: str):
    contexto = "\n".join(normas)
    prompt = f"Baseado nas seguintes normas:\n{contexto}\n\nResponda: {pergunta}"
    response = gemini_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    return response.text

@track_pipeline(run_name="Consulta_Normas_RAG")
def responder_duvida_tecnica(pergunta: str):
    normas = buscar_normas(pergunta)
    resposta = gerar_resposta_gemini(normas, pergunta)
    return resposta
```

---

### Exemplo C: Endpoint FastAPI Assíncrono (`async def`)
```python
from fastapi import FastAPI
from light_mlflow import LightMLflowConfig
from light_mlflow.decorators import track_pipeline, tool_span, llm_span
import asyncio

app = FastAPI(title="API Agente Light")

# Setup único no startup
LightMLflowConfig.setup(experiment_name="Light_Assistente_Virtual_API")

@tool_span(name="Verificar_Disponibilidade_Rede")
async def verificar_rede(cep: str):
    await asyncio.sleep(0.2)  # Simula request async
    return {"cep": cep, "rede_estavel": True}

@llm_span(name="LLM_Inferencia")
async def inferencia_llm(contexto: dict, mensagem: str):
    await asyncio.sleep(0.5)
    return f"Sua rede no CEP {contexto['cep']} está operando normalmente."

@track_pipeline(run_name="Webhook_Mensagem_Usuario")
async def fluxo_chat(mensagem: str, cep: str):
    rede = await verificar_rede(cep)
    resposta = await inferencia_llm(rede, mensagem)
    return resposta

@app.post("/chat")
async def chat_endpoint(mensagem: str, cep: str):
    resposta = await fluxo_chat(mensagem, cep)
    return {"resposta": resposta}
```

---

## 🟢 7. Integração Node.js / TypeScript (Apenas Backend)

Para serviços em Node.js (Express, NestJS, Fastify), utilize o pacote NPM corporativo com OpenTelemetry integrado:

### Instalação:
```bash
npm install git+https://github.com/Renanfavaro1/MLflow_Light.git#subdirectory=sdk-node
```

### Exemplo de Uso:
```javascript
import { LightMLflowConfig, trackPipeline, llmSpan, toolSpan } from 'light-mlflow-node';

// Setup inicial no boot da aplicação
await LightMLflowConfig.setup("Nome_do_Projeto_Node");

const buscarSAP = toolSpan("Buscar_Dados_SAP", async (cpf) => {
    return { saldo: 150.00, status: "Adimplente" };
});

const chamarIA = llmSpan("Gemini_Resumo", async (dados) => {
    // Retorno do SDK do Google GenAI com usageMetadata para tokens automáticos
    return {
        text: `Seu saldo é R$ ${dados.saldo}.`,
        usageMetadata: { promptTokenCount: 80, candidatesTokenCount: 20, totalTokenCount: 100 }
    };
});

const endpointAtendimento = trackPipeline("Atendimento_Node", async (req) => {
    const dados = await buscarSAP(req.body.cpf);
    const resposta = await chamarIA(dados);
    return resposta;
});
```

---

## 🛡️ 8. Resumo para Apresentações e Checklist de Entrega

| Item | Status / Padrão Oficial |
|---|---|
| **Painel Web (GCP)** | `https://mlflow-tracking-server-504082412074.us-central1.run.app` |
| **Login Web** | `light` / `Light@2026` |
| **Token SDK** | Recuperado do GCP Secret Manager: `mlflow-api-token` |
| **Instalação Python** | `pip install git+https://github.com/Renanfavaro1/MLflow_Light.git#subdirectory=sdk` |
| **Arquivo Claude Code** | Copiar este arquivo como `CLAUDE.md` na raiz do projeto |
| **Decorador Raiz** | `@track_pipeline(run_name="...")` (sempre na função principal) |
| **Decoradores Spans** | `@llm_span`, `@tool_span`, `@retriever_span`, `@agent_span` |
| **Cálculo de Tokens** | Automático para Anthropic Claude, Google Gemini e OpenAI |
| **Cálculo de Custos** | Automático em dólar ($) na árvore de Spans |
| **Tolerância a Falhas** | Fail-safe: o negócio nunca para se a telemetria oscilar |
