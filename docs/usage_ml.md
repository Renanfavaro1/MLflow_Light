# Guia Rápido: Modelos Tradicionais

Para modelos como Scikit-Learn e XGBoost, utilize o `@train_model`.
Ele ativará o **autolog**, que captura hiperparâmetros (como `max_depth`, `n_estimators`), salva as métricas de treino e faz o upload automático do arquivo do modelo (`.pkl`) para o Cloud Storage.

```python
from light_mlflow.decorators import train_model

@train_model(run_name="Treino_XGBoost")
def meu_treino():
    # Seu código normal...
    model.fit(X, y)
    return model
```
