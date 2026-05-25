import functools
import mlflow
import inspect
import logging
from typing import Optional

logger = logging.getLogger("light_mlflow.spans")

def _extract_and_log_tokens(response):
    """Extrai silenciosamente a contagem de tokens de respostas do Gemini/OpenAI e envia para o MLflow."""
    try:
        # Extração para SDK nativo do Google Gemini (usage_metadata)
        if hasattr(response, "usage_metadata") and response.usage_metadata is not None:
            usage = response.usage_metadata
            p_tokens = getattr(usage, "prompt_token_count", 0)
            c_tokens = getattr(usage, "candidates_token_count", 0)
            t_tokens = getattr(usage, "total_token_count", p_tokens + c_tokens)
            
            mlflow.log_metric("llm.usage.prompt_tokens", p_tokens)
            mlflow.log_metric("llm.usage.completion_tokens", c_tokens)
            mlflow.log_metric("llm.usage.total_tokens", t_tokens)
            
        # Extração para SDK nativo da OpenAI (usage)
        elif hasattr(response, "usage") and response.usage is not None:
            usage = response.usage
            p_tokens = getattr(usage, "prompt_tokens", 0)
            c_tokens = getattr(usage, "completion_tokens", 0)
            t_tokens = getattr(usage, "total_tokens", p_tokens + c_tokens)
            
            mlflow.log_metric("llm.usage.prompt_tokens", p_tokens)
            mlflow.log_metric("llm.usage.completion_tokens", c_tokens)
            mlflow.log_metric("llm.usage.total_tokens", t_tokens)
            
    except Exception as e:
        logger.warning(f"Aviso: Falha ao extrair métricas de tokens da resposta LLM. Erro: {e}")

def _trace_with_type(span_type: str, name: Optional[str] = None):
    """Factory interno para gerar decorators baseados no tipo do span."""
    def decorator(func):
        span_name = name or func.__name__
        # Utilizamos o mlflow.trace nativo do MLflow
        # Ele cuida magicamente de encadear spans (pai/filho) baseado na pilha de execução do Python.
        return mlflow.trace(name=span_name, span_type=span_type)(func)
    return decorator

# ==============================================================================
# SPANS GENAI - Componentes granulares para RAGs e Agentes
# ==============================================================================

def retriever_span(name: Optional[str] = None):
    """
    Rastreia a busca de documentos de contexto.
    Ex: Uma função que faz busca em um banco vetorial ou no Elasticsearch.
    """
    return _trace_with_type("RETRIEVER", name)

def chain_span(name: Optional[str] = None):
    """
    Rastreia uma cadeia sequencial de operações (como RAG chain, Chain of Thought).
    """
    return _trace_with_type("CHAIN", name)

def agent_span(name: Optional[str] = None):
    """
    Rastreia o raciocínio de um Agente Autônomo.
    Engloba as decisões sobre quais ferramentas chamar baseado na resposta da LLM.
    """
    return _trace_with_type("AGENT", name)

def tool_span(name: Optional[str] = None):
    """
    Rastreia a execução de uma ferramenta/tool disparada por um Agente.
    Ex: 'Consultar banco SQL', 'Buscar clima na web'.
    """
    return _trace_with_type("TOOL", name)

def llm_span(name: Optional[str] = None):
    """
    Rastreia uma chamada a LLM (Gemini, OpenAI) como um passo de um processo maior.
    Extrai magicamente os gastos de Tokens (se a função retornar o objeto nativo)
    e envia para o painel 'Metrics' do MLflow.
    """
    def decorator(func):
        span_name = name or func.__name__
        
        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                response = await func(*args, **kwargs)
                _extract_and_log_tokens(response)
                return response
            return mlflow.trace(name=span_name, span_type="LLM")(async_wrapper)
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                response = func(*args, **kwargs)
                _extract_and_log_tokens(response)
                return response
            return mlflow.trace(name=span_name, span_type="LLM")(sync_wrapper)
            
    return decorator

# ==============================================================================
# ORQUESTRADOR RAIZ
# ==============================================================================

def track_pipeline(run_name: str = "pipeline_execution"):
    """
    Decorator de alto nível para a função principal do seu software de IA.
    Ele cria o "Run" no MLflow e, ao mesmo tempo, cria o Span Raiz (CHAIN) que
    vai abraçar todos os outros Spans (Retriever, LLM, Agent) acionados abaixo dele.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 1. Inicia o Run (O agrupador master que vai aparecer na tela inicial do MLflow)
            with mlflow.start_run(run_name=run_name):
                
                # 2. Transforma a função executada no nó principal da árvore de Spans
                @mlflow.trace(name=func.__name__, span_type="CHAIN")
                def inner_execute():
                    return func(*args, **kwargs)
                
                return inner_execute()
        return wrapper
    return decorator
