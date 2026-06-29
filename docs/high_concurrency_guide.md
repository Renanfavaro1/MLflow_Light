# Guia de Alta Concorrência: Assistente Virtual + MLflow

Este guia destina-se a aplicações de altíssimo tráfego (como o Assistente Virtual rodando em FastAPI), onde milhares de chamadas de inferência de LLM ou chamadas de ferramentas ocorrem concorrentemente.

## O Desafio
Os decoradores padrões do SDK (`@llm_span`, `@track_pipeline`) são projetados para simplicidade e **bloqueiam a thread** enquanto enviam os dados de telemetria para o servidor remoto do MLflow via HTTP.
Em um cenário de mil requisições simultâneas, esperar o retorno da API do MLflow pode aumentar o tempo de resposta do chatbot (latência) ou gerar gargalos no seu event loop.

## A Solução: FastAPI BackgroundTasks
A melhor prática para não impactar o usuário final do Assistente Virtual é executar a cadeia de raciocínio (ou rastreamento principal) e delegar o envio ao MLflow para o background de forma assíncrona. 
Felizmente, no Cloud Run com CPU "Always On" (padrão em aplicações de alto tráfego) e no FastAPI, as `BackgroundTasks` são perfeitas para isso.

### Exemplo Arquitetural

```python
from fastapi import FastAPI, BackgroundTasks
from light_mlflow.decorators import track_pipeline, llm_span
from light_mlflow import LightMLflowConfig
import asyncio

app = FastAPI()
LightMLflowConfig.setup(experiment_name="Assistente_Virtual_Producao")

# 1. Suas lógicas de negócio ficam isoladas, porém instrumentadas:
@llm_span(name="Gerador_Resposta_Gemini")
async def gerar_resposta(pergunta: str):
    # Simula chamada a API da OpenAI/Google
    await asyncio.sleep(1)
    return "Resposta processada!"

@track_pipeline(run_name="Interacao_Usuario_Chatbot")
async def fluxo_principal(pergunta: str):
    # Essa função orquestra as tools e o LLM e será rastreada.
    resposta = await gerar_resposta(pergunta)
    return resposta

# 2. O Endpoint do FastAPI apenas enfileira o rastreamento!
@app.post("/chat")
async def chat_endpoint(pergunta: str, bg_tasks: BackgroundTasks):
    
    # Executar a lógica dentro do ciclo de background (forma fire-and-forget controlada)
    # NOTA: O FastAPI só enviará o processamento após responder o JSON 200 pro usuário.
    # No entanto, caso você precise do resultado do LLM *para* o usuário na mesma hora,
    # você processa o LLM na frente, e faz o log de metadados em background (Opção Avançada).
    
    bg_tasks.add_task(fluxo_principal, pergunta)
    return {"status": "Processamento iniciado no background."}
```

### Tolerância a Falhas do SDK
O SDK `light_mlflow` já está configurado para efetuar múltiplas retentativas exponenciais (`MLFLOW_HTTP_REQUEST_MAX_RETRIES=10`) caso o servidor do MLflow esteja sobrecarregado (HTTP 429), garantindo que seu dado não se perca durante um pico extremo de conexões.
