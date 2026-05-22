# Exemplos de Uso - Light MLflow SDK

Esta pasta contém exemplos práticos de como utilizar as ferramentas do SDK `light-mlflow`.

1. **`ml_model_example.py`**: Mostra como rastrear o treinamento de modelos tradicionais (Sklearn/XGBoost) com autolog.
2. **`rag_pipeline_example.py`**: Demonstra o uso de `Spans` aninhados para criar árvores de rastreamento para pipelines GenAI complexos.
3. **`llm_judge_example.py`**: Mostra como implementar o padrão "LLM as a Judge" para avaliar respostas de LLMs automaticamente usando o nosso decorator.

Para rodar qualquer um, certifique-se de ter instalado o SDK localmente (`pip install -e ./sdk`).
