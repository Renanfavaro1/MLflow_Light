import functools
import time
import mlflow
import logging

logger = logging.getLogger("light_mlflow.decorators")

def track_run(run_name: str = None, tags: dict = None):
    """
    Decorator base para transformar qualquer função em um Run do MLflow.
    Registra automaticamente o tempo de execução, os parâmetros passados e o status (sucesso/erro).
    
    Args:
        run_name (str): Nome do Run. Se None, usará o nome da função.
        tags (dict): Dicionário com tags adicionais para categorizar o Run.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            name = run_name or func.__name__
            
            # Inicia o contexto do MLflow
            with mlflow.start_run(run_name=name) as run:
                if tags:
                    mlflow.set_tags(tags)
                
                # Registra os kwargs como parâmetros no MLflow (limitando a strings curtas para evitar quebra)
                try:
                    safe_kwargs = {k: str(v) for k, v in kwargs.items() if len(str(v)) < 250}
                    if safe_kwargs:
                        mlflow.log_params(safe_kwargs)
                except Exception as e:
                    logger.warning(f"Não foi possível logar os parâmetros: {e}")

                start_time = time.time()
                status = "success"
                
                try:
                    # Executa a função original
                    result = func(*args, **kwargs)
                    return result
                
                except Exception as e:
                    # Captura erros e registra no MLflow antes de repassar a exceção
                    status = "failed"
                    mlflow.set_tag("error_message", str(e))
                    mlflow.set_tag("error_type", type(e).__name__)
                    raise
                
                finally:
                    # Registra a métrica de tempo e status sempre, dando erro ou não
                    duration = time.time() - start_time
                    mlflow.log_metric("execution_duration_seconds", duration)
                    mlflow.set_tag("status", status)
                    
        return wrapper
    return decorator

