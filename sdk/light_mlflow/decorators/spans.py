import functools
import mlflow
from typing import Optional

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
    Rastreia uma chamada a LLM (Gemini, OpenAI) apenas como um passo de um processo maior.
    (Diferente do @track_llm_call da Fase 6, que inicia um Run inteiro só pra LLM).
    """
    return _trace_with_type("LLM", name)

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
