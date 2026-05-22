import mlflow
import json
import logging
from typing import Callable, Dict, Any
import functools

logger = logging.getLogger("light_mlflow.evaluation")

class JudgeCriteria:
    """Constantes para critérios padrão de avaliação do LLM as a Judge."""
    RELEVANCE = "relevance"
    FAITHFULNESS = "faithfulness"
    COHERENCE = "coherence"
    COMPLETENESS = "completeness"
    HARMFULNESS = "harmfulness"

class LLMJudge:
    """
    Framework para avaliar a qualidade das respostas de uma LLM usando outra LLM (ou a mesma).
    O LLM Judge gera notas e justificativas, salvando-as automaticamente no MLflow.
    """
    def __init__(self, evaluator_func: Callable[[str, str, str], Dict[str, Any]]):
        """
        Inicializa o Juiz LLM.
        
        Args:
            evaluator_func: Uma função fornecida pelo Cientista de Dados que faz a chamada 
                            real para o Gemini/OpenAI pedindo para avaliar o texto. 
                            Deve receber (input_text, output_text, context) e retornar
                            um dict com {'score': int (1-5), 'justification': str}.
        """
        self.evaluator_func = evaluator_func

    def evaluate(self, input_text: str, output_text: str, context: str = "", criterion: str = JudgeCriteria.RELEVANCE):
        """
        Avalia uma única interação (pergunta -> resposta) e registra a nota no MLflow.
        """
        logger.info(f"⚖️ LLM Judge iniciando avaliação do critério: {criterion}")
        try:
            # Chama a função do Cientista de Dados (que bate na API do Gemini/OpenAI para avaliar)
            result = self.evaluator_func(input_text, output_text, context)
            
            score = result.get('score', 0)
            justification = result.get('justification', '')
            
            # Registra a métrica quantitativa no painel principal do MLflow
            mlflow.log_metric(f"judge_score_{criterion}", score)
            
            # Salva a justificativa em texto longo nos artefatos
            mlflow.log_text(
                json.dumps(result, indent=2, ensure_ascii=False),
                f"evaluations/{criterion}_justification.json"
            )
                
            return result
            
        except Exception as e:
            logger.error(f"❌ Erro durante a avaliação do LLM Judge: {e}")
            return None


def judge_output(judge: LLMJudge, criterion: str = JudgeCriteria.RELEVANCE):
    """
    Decorator mágico que avalia o output de uma função automaticamente sem precisar de código extra.
    
    Exemplo:
    @judge_output(meu_juiz, criterion=JudgeCriteria.FAITHFULNESS)
    def responder_cliente(prompt):
        return gemini.generate(prompt)
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 1. Deixa a função gerar a resposta original
            output = func(*args, **kwargs)
            
            # 2. Descobre qual foi o input (a pergunta)
            input_text = kwargs.get('prompt') or kwargs.get('input_text') or (args[0] if args else "")
            
            # 3. Chama o juiz silenciosamente no mesmo Run para dar a nota
            if mlflow.active_run():
                judge.evaluate(str(input_text), str(output), criterion=criterion)
            else:
                with mlflow.start_run(run_name="auto_evaluation"):
                    judge.evaluate(str(input_text), str(output), criterion=criterion)
            
            return output
        return wrapper
    return decorator
