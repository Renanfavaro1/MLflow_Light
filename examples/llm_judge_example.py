from light_mlflow import LightMLflowConfig
from light_mlflow.evaluation import LLMJudge, JudgeCriteria, judge_output

LightMLflowConfig.setup(experiment_name="Avaliacao_Automatica")

def meu_avaliador_gemini(input_text, output_text, context):
    """
    Aqui você faria a chamada real para a API do Gemini, pedindo para ele dar 
    uma nota de 1 a 5 baseado no critério.
    """
    # Simulando a resposta do Gemini:
    return {
        "score": 4, 
        "justification": "A resposta é boa, mas não cita a segunda via pelo site."
    }

# Inicializa a classe do Juiz
juiz = LLMJudge(evaluator_func=meu_avaliador_gemini)

# Aplica o decorator na função do seu chatbot
@judge_output(juiz, criterion=JudgeCriteria.COMPLETENESS)
def responder_cliente(prompt):
    return "Você pode pedir a segunda via pelo App da Light."

if __name__ == "__main__":
    # Ao executar isso, o MLflow registrará o prompt, a resposta e, em seguida,
    # chamará o juiz para dar a nota e salvará no painel.
    responder_cliente(prompt="Como peço segunda via?")
