from light_mlflow import LightMLflowConfig
from light_mlflow.decorators import track_pipeline, agent_span, tool_span, llm_span
import time

LightMLflowConfig.setup(experiment_name="Light_Agente_Resolucao")

@tool_span(name="Consultar_Fatura_API")
def buscar_fatura(cpf):
    time.sleep(0.3)
    return {"status": "atrasada", "valor": 150.00}

@llm_span(name="Gemini_Decisao")
def gemini_decidir_acao(contexto):
    time.sleep(1)
    if contexto["status"] == "atrasada":
        return "Gerar código de barras"
    return "Avisar que está tudo certo"

@agent_span(name="Agente_Financeiro")
def agente_loop(cpf):
    fatura = buscar_fatura(cpf)
    decisao = gemini_decidir_acao(fatura)
    return decisao

@track_pipeline(run_name="Atendimento_Agente_Autonomo")
def chat_agente(cpf):
    resultado = agente_loop(cpf)
    return resultado

if __name__ == "__main__":
    print(chat_agente("123.456.789-00"))
