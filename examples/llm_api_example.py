from light_mlflow import LightMLflowConfig
from light_mlflow.decorators import track_llm_call
import time

LightMLflowConfig.setup(experiment_name="Light_LLM_APIs")

# O decorator registra o prompt, o tempo de resposta, e a resposta final.
@track_llm_call(model_name="gemini-1.5-pro", track_prompt=True)
def classificar_sentimento(prompt):
    print("Chamando a API do Gemini...")
    time.sleep(1) # Simula a chamada de rede
    
    if "ruim" in prompt.lower():
        return "NEGATIVO"
    return "POSITIVO"

if __name__ == "__main__":
    resultado = classificar_sentimento(prompt="O atendimento hoje foi muito ruim, a luz não voltou.")
    print(f"Resultado: {resultado}")
