import functools
import mlflow
import logging

logger = logging.getLogger("light_mlflow.decorators")

def train_model(run_name: str = "model_training", autolog: bool = True):
    """
    Decorator para simplificar o treinamento de modelos de Machine Learning (Classificação/Regressão).
    Ele ativa o autolog() nativo do MLflow para capturar automaticamente os hiperparâmetros, 
    métricas de treinamento e o artefato do modelo treinado (seja sklearn, xgboost, pytorch, etc).
    
    Args:
        run_name (str): Nome do Run no MLflow.
        autolog (bool): Se True, ativa a captura automática global do MLflow.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 1. Ativa o autolog global (detecta automaticamente scikit-learn, xgboost, pytorch, keras, etc)
            if autolog:
                try:
                    mlflow.autolog()
                except Exception as e:
                    logger.warning(f"Aviso: Não foi possível ativar o autolog global. Erro: {e}")

            # 2. Inicia o Run para o treinamento
            name = run_name or func.__name__
            with mlflow.start_run(run_name=name) as run:
                mlflow.set_tag("task_type", "training")
                
                # 3. Executa a função de treinamento
                model_result = func(*args, **kwargs)
                
                return model_result
        return wrapper
    return decorator
