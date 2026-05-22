# Guia Rápido: LLM as a Judge

Para avaliar automaticamente a qualidade das respostas do seu Chatbot/RAG usando a própria inteligência artificial, use o `LLMJudge`.

## 1. Defina o seu avaliador (A IA que julga)
Você precisa criar uma função simples que chama a API (do Gemini, por exemplo) e pede pra ele dar uma nota de 1 a 5 baseada num critério (Relevância, Coerência).

```python
def gemini_avaliador(input_text, output_text, context):
    # Faz o request para o Gemini pedindo a nota
    return {"score": 5, "justification": "Resposta perfeita e clara."}
```

## 2. Aplique o Decorator
Importe a classe e coloque o decorator `@judge_output` na sua função principal do Chatbot:

```python
from light_mlflow.evaluation import LLMJudge, JudgeCriteria, judge_output

juiz = LLMJudge(evaluator_func=gemini_avaliador)

@judge_output(juiz, criterion=JudgeCriteria.RELEVANCE)
def meu_chatbot(prompt):
    return "Resposta do meu bot..."
```

O MLflow criará automaticamente um Span chamado `llm_judge_relevance`, salvará a nota em um gráfico e gravará a justificativa como um arquivo `.json`.
