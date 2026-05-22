import functools
import time
import mlflow
import logging

logger = logging.getLogger("light_mlflow.decorators")

def track_llm_call(run_name: str = "llm_call", model_name: str = "unknown", track_prompt: bool = True):
    """
    Decorator simplificado para registrar chamadas diretas a APIs de LLM (Gemini, OpenAI, etc).
    Registra latência, o modelo utilizado e, opcionalmente, os prompts e respostas no MLflow.
    
    Ideal para scripts isolados ou APIs simples que não usam frameworks como LangChain.
    Para pipelines complexos (RAG/Agentes), utilize os Spans (Phase 7).
    
    Args:
        run_name (str): Nome do Run no MLflow.
        model_name (str): Nome do modelo (ex: 'gemini-1.5-pro').
        track_prompt (bool): Se True, salva o texto do prompt e a resposta no MLflow.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            name = run_name or func.__name__
            with mlflow.start_run(run_name=name) as run:
                mlflow.set_tag("task_type", "llm_inference")
                mlflow.set_tag("llm.model_name", model_name)
                
                # Tenta capturar o prompt de entrada (via kwarg 'prompt' ou o primeiro argumento posicional)
                if track_prompt:
                    prompt = kwargs.get('prompt') or (args[0] if args else None)
                    if prompt:
                        # Salva como artefato de texto para não bater no limite de caracteres do MLflow
                        mlflow.log_text(str(prompt), "inputs/prompt.txt")
                
                start_time = time.time()
                try:
                    # Executa a chamada real para a LLM
                    response = func(*args, **kwargs)
                    
                    # Salva a resposta gerada
                    if track_prompt and response:
                        mlflow.log_text(str(response), "outputs/response.txt")
                        
                    mlflow.set_tag("status", "success")
                    return response
                
                except Exception as e:
                    mlflow.set_tag("status", "failed")
                    mlflow.set_tag("error_message", str(e))
                    raise e
                
                finally:
                    duration = time.time() - start_time
                    mlflow.log_metric("llm.latency_seconds", duration)
        return wrapper
    return decorator
