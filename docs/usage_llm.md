# Guia Rápido: LLM Tracker Básico

Se você tem um script Python simples que faz chamadas diretas para a API do Gemini ou da OpenAI (sem usar LangChain), use o `@track_llm_call`.

Esse decorator salva:
- O modelo usado (`model_name`)
- A latência da chamada da API
- O prompt enviado (como texto nos artefatos)
- A resposta final gerada (como texto nos artefatos)

```python
from light_mlflow.decorators import track_llm_call

@track_llm_call(model_name="gemini-1.5-pro")
def classificar_texto(prompt):
    # chamada para a API
    return resposta
```
