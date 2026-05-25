# Integração Light MLflow para Agentes Autônomos

## 📌 Objetivo
Este guia serve como a principal base de conhecimento para o Antigravity (ou outras IAs) aprenderem a integrar o SDK padrão de Observabilidade da Light (`light_mlflow`) em novos projetos de Agentes de IA, RAGs e orquestradores.

## 📦 1. Dependência e Instalação
Ao criar ou atualizar um projeto Python, o pacote do MLflow da Light deve ser inserido no arquivo `requirements.txt` utilizando o repositório Git:

```text
# Adicionar no requirements.txt
light-mlflow @ git+https://github.com/Renanfavaro1/MLflow_Light.git#subdirectory=sdk
```

## ⚙️ 2. Configuração no Código (Startup)
Em todo novo projeto (seja FastAPI, Flask, ou scripts batch), o MLflow deve ser inicializado **uma única vez** no startup da aplicação, antes de qualquer execução de IA:

```python
from light_mlflow import LightMLflowConfig

# A URI de conexão com o banco/servidor será injetada automaticamente 
# pelas variáveis de ambiente do Cloud Run (MLFLOW_TRACKING_URI).
LightMLflowConfig.setup(experiment_name="Nome_do_Projeto_Novo")
```

## 🔍 3. Rastreamento Nativo (Traces) para Agentes
Para fluxos agenticos e RAGs, a IA desenvolvedora deve utilizar **EXCLUSIVAMENTE** a arquitetura de `spans` baseada em decoradores. Isso fará com que o painel do MLflow gere uma árvore visual detalhada (Traces) mostrando latência, prompts e ferramentas acionadas.

### Importação Padrão:
```python
from light_mlflow.decorators import track_pipeline, agent_span, tool_span, llm_span, retriever_span
```

### Regras Estritas de Aplicação (Para a IA Desenvolvedora)
1. **`@track_pipeline(run_name="...")`**: DEVE ser colocado apenas na **função principal** ou endpoint de entrada (ex: `chat()`, `main()`). Ele é o orquestrador que abre a gravação. Não use `mlflow.start_run()` manualmente.
2. **`@retriever_span(name="...")`**: Obrigatório em funções de busca (Elasticsearch, Pinecone, buscas em banco de dados para RAG).
3. **`@llm_span(name="...")`**: Obrigatório nas funções que enviam o prompt e recebem a resposta do provedor de IA (Gemini, VertexAI, OpenAI).
4. **`@tool_span(name="...")`**: Obrigatório em qualquer ferramenta consumida pelo Agente (ex: consultar_saldo_sap, buscar_clima).
5. **`@agent_span(name="...")`**: Opcional, usado para encapsular a lógica de raciocínio interno/loops de agentes ReAct.

### Exemplo Arquitetural a Ser Seguido
```python
from light_mlflow.decorators import track_pipeline, tool_span, llm_span

@tool_span(name="Consultar_Faturas_SAP")
def buscar_faturas(cpf):
    # Lógica de integração externa
    return f"Faturas abertas para {cpf}: R$ 150,00"

@llm_span(name="Gemini_Gerador_Resposta")
def gerar_resposta_ao_cliente(contexto, pergunta):
    # Inferência LLM
    return f"Baseado no sistema: {contexto}"

@track_pipeline(run_name="Atendimento_Cliente_Fluxo")
def processar_mensagem(pergunta, cpf):
    contexto = buscar_faturas(cpf)
    resposta = gerar_resposta_ao_cliente(contexto, pergunta)
    return resposta
```

## 🚨 Atenção (Avisos Críticos de Arquitetura)
- **Não misturar abordagens**: NUNCA utilize o antigo `@track_llm_call` em projetos com Agentes, pois ele não gera a árvore hierárquica na aba Traces.
- **Evite hardcode de URLs**: Nunca defina a `tracking_uri` manualmente no código. Deixe o SDK ler da variável de ambiente gerenciada pelo Terraform/Cloud Run.
- **Segurança de SSL**: Em caso de avisos de `InsecureRequestWarning` devido à rede interna da Light, não desative os warnings no código do agente (deixe isso para a camada de infra/Docker se necessário, ou garanta que o CA corporativo esteja instalado).
