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

MODEL_PRICES = {
    'claude-opus-4.7': {'input': 4.82, 'output': 23.80},
    'claude-opus-4.6': {'input': 4.82, 'output': 23.80},
    'claude-sonnet-4.6': {'input': 2.80, 'output': 14.30},
    'claude-opus-4.5': {'input': 4.82, 'output': 23.80},
    'claude-sonnet-4.5': {'input': 2.80, 'output': 14.30},
    'claude-haiku-4.5': {'input': 0.95, 'output': 4.80},
    'claude-sonnet-4': {'input': 3.00, 'output': 15.00},
    'claude-3.5-haiku': {'input': 0.80, 'output': 4.00},
    'gpt-5.5': {'input': 5.00, 'output': 30.00},
    'gpt-5.4-pro': {'input': 30.00, 'output': 180.00},
    'gpt-5.4': {'input': 2.50, 'output': 15.00},
    'gpt-5.3-codex': {'input': 1.80, 'output': 14.00},
    'gpt-5.3-chat': {'input': 1.80, 'output': 14.00},
    'gpt-5.4-nano': {'input': 0.20, 'output': 1.30},
    'gpt-5.4-mini': {'input': 0.75, 'output': 4.50},
    'gpt-5.1': {'input': 1.30, 'output': 10.00},
    'gemini-3.1-pro-preview': {'input': 2.00, 'output': 12.00},
    'gemini-3.5-flash': {'input': 1.50, 'output': 9.00},
    'gemini-3.1-flash-lite': {'input': 0.25, 'output': 1.50},
    'gemini-3.1-flash-lite-preview': {'input': 0.25, 'output': 1.50},
    'gemini-3-pro-image-preview': {'input': 2.00, 'output': 12.00},
    'gemini-2.5-flash': {'input': 0.30, 'output': 2.50},
    'gemini-2.5-pro': {'input': 1.30, 'output': 10.00},
    'gemini-1.5-flash': {'input': 0.075, 'output': 0.30},
    'gemini-1.5-pro': {'input': 1.25, 'output': 5.00},
    'gemini-1.0-pro': {'input': 0.50, 'output': 1.50},
    'gpt-4o': {'input': 2.50, 'output': 10.00},
    'gpt-4o-mini': {'input': 0.15, 'output': 0.60},
    'default': {'input': 0.075, 'output': 0.30}
}

def _get_prices_for_model(model_name: Optional[str]) -> dict:
    if not model_name or not isinstance(model_name, str):
        return MODEL_PRICES['default']
    lower_name = model_name.lower()
    for key, prices in MODEL_PRICES.items():
        if key != 'default' and key in lower_name:
            return prices
    return MODEL_PRICES['default']

def _extract_and_log_tokens(response, span=None):
    """Extrai silenciosamente a contagem de tokens de respostas do Gemini/OpenAI, calcula custos e envia para o MLflow."""
    try:
        p_tokens, c_tokens, t_tokens = 0, 0, 0
        has_tokens = False

        # Extração para SDK nativo do Google Gemini (usage_metadata)
        if hasattr(response, "usage_metadata") and response.usage_metadata is not None:
            usage = response.usage_metadata
            p_tokens = getattr(usage, "prompt_token_count", 0)
            c_tokens = getattr(usage, "candidates_token_count", 0)
            t_tokens = getattr(usage, "total_token_count", p_tokens + c_tokens)
            has_tokens = True
            
        # Extração para SDK nativo da OpenAI (usage)
        elif hasattr(response, "usage") and response.usage is not None:
            usage = response.usage
            p_tokens = getattr(usage, "prompt_tokens", 0)
            c_tokens = getattr(usage, "completion_tokens", 0)
            t_tokens = getattr(usage, "total_tokens", p_tokens + c_tokens)
            has_tokens = True

        if has_tokens and t_tokens > 0:
            mlflow.log_metric("llm.usage.prompt_tokens", p_tokens)
            mlflow.log_metric("llm.usage.completion_tokens", c_tokens)
            mlflow.log_metric("llm.usage.total_tokens", t_tokens)
            
            # Adiciona no Span para aparecer na UI do Trace
            if span:
                span.set_attribute("llm.usage.prompt_tokens", p_tokens)
                span.set_attribute("llm.usage.completion_tokens", c_tokens)
                span.set_attribute("llm.usage.total_tokens", t_tokens)
                
                # Atributos de convenção semântica padrão da OpenTelemetry GenAI (necessários para a interface moderna do MLflow)
                span.set_attribute("gen_ai.usage.prompt_tokens", p_tokens)
                span.set_attribute("gen_ai.usage.completion_tokens", c_tokens)
                span.set_attribute("gen_ai.usage.total_tokens", t_tokens)

            # Extrair nome do modelo e calcular custos
            model_name = getattr(response, "model", None) or getattr(response, "model_name", None) or 'gemini-2.5-flash'
            prices = _get_prices_for_model(model_name)
            input_cost = (p_tokens * prices['input']) / 1000000.0
            output_cost = (c_tokens * prices['output']) / 1000000.0
            total_cost = input_cost + output_cost

            mlflow.log_metric("llm.cost.input_cost", input_cost)
            mlflow.log_metric("llm.cost.output_cost", output_cost)
            mlflow.log_metric("llm.cost.total_cost", total_cost)

            if span:
                span.set_attribute("mlflow.llm.cost", json.dumps({
                    "input_cost": input_cost,
                    "output_cost": output_cost,
                    "total_cost": total_cost
                }))
                span.set_attribute("mlflow.llm.model", model_name)
                span.set_attribute("mlflow.llm.provider", "google" if "gemini" in model_name.lower() else ("anthropic" if "claude" in model_name.lower() else "openai"))
                span.set_attribute("gen_ai.request.model", model_name)
                span.set_attribute("gen_ai.response.model", model_name)
            
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

def _get_contents_from_args_kwargs(args, kwargs):
    # 1. Verifica se 'contents' está em kwargs
    if "contents" in kwargs:
        return kwargs["contents"]
    
    # 2. Varre os argumentos posicionais pulando instâncias de classe (ex: self)
    for arg in args:
        if isinstance(arg, list):
            return arg
        if isinstance(arg, str):
            # Tenta evitar nomes de métodos de classe ou strings muito curtas
            if len(arg) > 5 and not arg.startswith("gemini-") and not arg.startswith("gpt-"):
                return arg
    return None

def _normalize_llm_span_data(args, kwargs, response):
    """
    Tenta normalizar os inputs/outputs do Google GenAI para o formato padrão do MLflow/OpenAI,
    permitindo que a UI de Traces renderize as ferramentas (tool calling) e chats perfeitamente.
    Suporta métodos de classe (self), respostas brutas, strings simples e dicts.
    """
    normalized_inputs = {"messages": []}
    normalized_outputs = {"choices": [{"message": {"role": "assistant", "content": "", "tool_calls": []}}]}
    
    try:
        # Processa Inputs
        contents = _get_contents_from_args_kwargs(args, kwargs)
        
        if isinstance(contents, list):
            for c in contents:
                if isinstance(c, dict):
                    role = c.get("role", "user")
                    if role == "model": role = "assistant"
                    text_content = c.get("content", "")
                    normalized_inputs["messages"].append({"role": role, "content": text_content.strip()})
                    continue

                role = getattr(c, "role", "user")
                if role == "model": role = "assistant"
                
                text_content = ""
                parts = getattr(c, "parts", [])
                for p in parts:
                    if hasattr(p, "text") and p.text:
                        text_content += p.text
                    elif hasattr(p, "function_response") and p.function_response:
                        resp_val = getattr(p.function_response, "response", {})
                        text_content += f"\n[Function Response: {getattr(p.function_response, 'name', '')} -> {resp_val}]"
                
                if not text_content and hasattr(c, "text") and c.text:
                    text_content = c.text

                normalized_inputs["messages"].append({"role": role, "content": text_content.strip()})
        elif isinstance(contents, str):
            normalized_inputs["messages"].append({"role": "user", "content": contents.strip()})
        else:
            return None, None
            
        # Processa Outputs
        if hasattr(response, "candidates") and response.candidates:
            cand = response.candidates[0]
            if hasattr(cand, "content") and cand.content:
                out_text = ""
                tool_calls = []
                parts = getattr(cand.content, "parts", [])
                for p in parts:
                    if hasattr(p, "text") and p.text:
                        out_text += p.text
                    elif hasattr(p, "function_call") and p.function_call:
                        fc = p.function_call
                        args_str = json.dumps(dict(fc.args)) if hasattr(fc, "args") and fc.args else "{}"
                        tool_calls.append({
                            "type": "function",
                            "function": {
                                "name": fc.name,
                                "arguments": args_str
                            }
                        })
                normalized_outputs["choices"][0]["message"]["content"] = out_text.strip()
                if tool_calls:
                    normalized_outputs["choices"][0]["message"]["tool_calls"] = tool_calls
            else:
                return None, None
        elif isinstance(response, str):
            normalized_outputs["choices"][0]["message"]["content"] = response.strip()
        else:
            return None, None
            
        # Tenta extrair Tokens para a raiz do output (padrão que a UI do MLflow lê nativamente)
        try:
            if hasattr(response, "usage_metadata") and response.usage_metadata is not None:
                usg = response.usage_metadata
                normalized_outputs["usage"] = {
                    "prompt_tokens": getattr(usg, "prompt_token_count", 0),
                    "completion_tokens": getattr(usg, "candidates_token_count", 0),
                    "total_tokens": getattr(usg, "total_token_count", 0)
                }
        except Exception:
            pass

        return normalized_inputs, normalized_outputs
    except Exception as e:
        logger.warning(f"Erro ao normalizar dados do span de LLM: {e}")
        return None, None

def llm_span(name: Optional[str] = None):
    """Rastreia uma chamada a LLM e extrai os gastos de Tokens."""
    def decorator(func):
        span_name = name or func.__name__
        
        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                with mlflow.start_span(name=span_name, span_type="LLM") as span:
                    try:
                        response = await func(*args, **kwargs)
                        
                        norm_in, norm_out = _normalize_llm_span_data(args, kwargs, response)
                        if norm_in and norm_out:
                            span.set_inputs(norm_in)
                            span.set_outputs(norm_out)
                        else:
                            span.set_inputs(_safe_serialize({"args": args, "kwargs": kwargs}))
                            span.set_outputs(_safe_serialize(response))
                            
                        _extract_and_log_tokens(response, span)
                        return response
                    except Exception as e:
                        span.set_inputs(_safe_serialize({"args": args, "kwargs": kwargs}))
                        span.set_status("ERROR")
                        raise e
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                with mlflow.start_span(name=span_name, span_type="LLM") as span:
                    try:
                        response = func(*args, **kwargs)
                        
                        norm_in, norm_out = _normalize_llm_span_data(args, kwargs, response)
                        if norm_in and norm_out:
                            span.set_inputs(norm_in)
                            span.set_outputs(norm_out)
                        else:
                            span.set_inputs(_safe_serialize({"args": args, "kwargs": kwargs}))
                            span.set_outputs(_safe_serialize(response))
                            
                        _extract_and_log_tokens(response, span)
                        return response
                    except Exception as e:
                        span.set_inputs(_safe_serialize({"args": args, "kwargs": kwargs}))
                        span.set_status("ERROR")
                        raise e
            return sync_wrapper
            
    return decorator

# ==============================================================================
# ORQUESTRADOR RAIZ
# ==============================================================================

def track_pipeline(run_name: str = "pipeline_execution", experiment_name: str = None):
    """Decorator de alto nível para a função principal. Inicia o Run e o Span raiz."""
    def decorator(func):
        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                exp_id = None
                if experiment_name:
                    exp = mlflow.get_experiment_by_name(experiment_name)
                    exp_id = exp.experiment_id if exp else mlflow.create_experiment(experiment_name)
                
                with mlflow.start_run(run_name=run_name, experiment_id=exp_id):
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
                exp_id = None
                if experiment_name:
                    exp = mlflow.get_experiment_by_name(experiment_name)
                    exp_id = exp.experiment_id if exp else mlflow.create_experiment(experiment_name)
                    
                with mlflow.start_run(run_name=run_name, experiment_id=exp_id):
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
