# Guia Rápido: Observabilidade Avançada de IA (Spans)

Quando construímos RAGs (Retrieval-Augmented Generation) ou Agentes, precisamos de **Tracing** em árvore, não apenas um log linear. O MLflow fornece isso de forma nativa e o SDK da Light facilita com decorators.

A regra de ouro é: **A função principal que desencadeia as outras deve ter o `@track_pipeline`**.

```python
from light_mlflow.decorators import track_pipeline, retriever_span, llm_span

@retriever_span()
def buscar():
    pass

@llm_span()
def gerar():
    pass

@track_pipeline()
def main():
    docs = buscar()
    gerar(docs)
```
No painel do MLflow (na aba Traces), você verá o `main` como o pai, e `buscar` e `gerar` como filhos, com as respectivas latências.
