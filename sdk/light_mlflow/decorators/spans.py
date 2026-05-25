import functools
import mlflow
import inspect
import logging
import json
from typing import Optional

logger = logging.getLogger("light_mlflow.spans")

def _safe_serialize(obj):
    """Garante que objetos complexos (bytes, Pydantic, etc) não quebrem o Trace do MLflow, transformando-os em dicionários navegáveis."""
    if isinstance(obj, dict):
        return {k: _safe_serialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_safe_serialize(v) for v in obj]
    if isinstance(obj, tuple):
        return tuple(_safe_serialize(v) for v in obj)
        
    # Tratamento para Pydantic / Google GenAI SDK
    if hasattr(obj, "model_dump"):
        try:
            return _safe_serialize(obj.model_dump())
        except Exception:
            pass
    elif hasattr(obj, "dict"):
        try:
            return _safe_serialize(obj.dict())
        except Exception:
            pass
            
    if isinstance(obj, bytes):
        return "<bytes_data>"
        
    try:
        json.dumps(obj)
        return obj
    except TypeError:
        return str(obj)

def _extract_and_log_tokens(response, span=None):
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
            
            # Adiciona no Span para aparecer na UI do Trace
            if span:
                span.set_attribute("llm.usage.prompt_tokens", p_tokens)
                span.set_attribute("llm.usage.completion_tokens", c_tokens)
                span.set_attribute("llm.usage.total_tokens", t_tokens)
            
        # Extração para SDK nativo da OpenAI (usage)
        elif hasattr(response, "usage") and response.usage is not None:
            usage = response.usage
            p_tokens = getattr(usage, "prompt_tokens", 0)
            c_tokens = getattr(usage, "completion_tokens", 0)
            t_tokens = getattr(usage, "total_tokens", p_tokens + c_tokens)
            
            mlflow.log_metric("llm.usage.prompt_tokens", p_tokens)
            mlflow.log_metric("llm.usage.completion_tokens", c_tokens)
            mlflow.log_metric("llm.usage.total_tokens", t_tokens)
            
            if span:
                span.set_attribute("llm.usage.prompt_tokens", p_tokens)
                span.set_attribute("llm.usage.completion_tokens", c_tokens)
                span.set_attribute("llm.usage.total_tokens", t_tokens)
            
    except Exception as e:
        logger.warning(f"Aviso: Falha ao extrair métricas de tokens da resposta LLM. Erro: {e}")

def _trace_with_type(span_type: str, name: Optional[str] = None):
    """Factory interno para gerar decorators baseados no tipo do span."""
    def decorator(func):
        span_name = name or func.__name__
        
        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                with mlflow.start_span(name=span_name, span_type=span_type) as span:
                    span.set_inputs(_safe_serialize({"args": args, "kwargs": kwargs}))
                    try:
                        res = await func(*args, **kwargs)
                        span.set_outputs(_safe_serialize(res))
                        return res
                    except Exception as e:
                        span.set_status("ERROR")
                        raise e
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                with mlflow.start_span(name=span_name, span_type=span_type) as span:
                    span.set_inputs(_safe_serialize({"args": args, "kwargs": kwargs}))
                    try:
                        res = func(*args, **kwargs)
                        span.set_outputs(_safe_serialize(res))
                        return res
                    except Exception as e:
                        span.set_status("ERROR")
                        raise e
            return sync_wrapper
    return decorator

# ==============================================================================
# SPANS GENAI - Componentes granulares para RAGs e Agentes
# ==============================================================================

def retriever_span(name: Optional[str] = None):
    """Rastreia a busca de documentos de contexto."""
    return _trace_with_type("RETRIEVER", name)

def chain_span(name: Optional[str] = None):
    """Rastreia uma cadeia sequencial de operações."""
    return _trace_with_type("CHAIN", name)

def agent_span(name: Optional[str] = None):
    """Rastreia o raciocínio de um Agente Autônomo."""
    return _trace_with_type("AGENT", name)

def tool_span(name: Optional[str] = None):
    """Rastreia a execução de uma ferramenta disparada por um Agente."""
    return _trace_with_type("TOOL", name)

def llm_span(name: Optional[str] = None):
    """Rastreia uma chamada a LLM e extrai os gastos de Tokens."""
    def decorator(func):
        span_name = name or func.__name__
        
        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                with mlflow.start_span(name=span_name, span_type="LLM") as span:
                    span.set_inputs(_safe_serialize({"args": args, "kwargs": kwargs}))
                    try:
                        response = await func(*args, **kwargs)
                        span.set_outputs(_safe_serialize(response))
                        _extract_and_log_tokens(response, span)
                        return response
                    except Exception as e:
                        span.set_status("ERROR")
                        raise e
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                with mlflow.start_span(name=span_name, span_type="LLM") as span:
                    span.set_inputs(_safe_serialize({"args": args, "kwargs": kwargs}))
                    try:
                        response = func(*args, **kwargs)
                        span.set_outputs(_safe_serialize(response))
                        _extract_and_log_tokens(response, span)
                        return response
                    except Exception as e:
                        span.set_status("ERROR")
                        raise e
            return sync_wrapper
            
    return decorator

# ==============================================================================
# ORQUESTRADOR RAIZ
# ==============================================================================

def track_pipeline(run_name: str = "pipeline_execution"):
    """Decorator de alto nível para a função principal. Inicia o Run e o Span raiz."""
    def decorator(func):
        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                with mlflow.start_run(run_name=run_name):
                    with mlflow.start_span(name=func.__name__, span_type="CHAIN") as span:
                        span.set_inputs(_safe_serialize({"args": args, "kwargs": kwargs}))
                        try:
                            res = await func(*args, **kwargs)
                            span.set_outputs(_safe_serialize(res))
                            return res
                        except Exception as e:
                            span.set_status("ERROR")
                            raise e
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                with mlflow.start_run(run_name=run_name):
                    with mlflow.start_span(name=func.__name__, span_type="CHAIN") as span:
                        span.set_inputs(_safe_serialize({"args": args, "kwargs": kwargs}))
                        try:
                            res = func(*args, **kwargs)
                            span.set_outputs(_safe_serialize(res))
                            return res
                        except Exception as e:
                            span.set_status("ERROR")
                            raise e
            return sync_wrapper
    return decorator
