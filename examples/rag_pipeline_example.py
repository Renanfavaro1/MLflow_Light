import time
from light_mlflow import LightMLflowConfig
from light_mlflow.decorators import track_pipeline, retriever_span, llm_span

LightMLflowConfig.setup(experiment_name="Light_RAG_Atendimento")

@retriever_span(name="Busca_Base_Conhecimento")
def buscar_documentos(pergunta):
    time.sleep(0.5) # Simulando busca no ElasticSearch
    return ["A Light atende a zona sul do RJ", "Segunda via pode ser pedida no app"]

@llm_span(name="Chamada_Gemini_Pro")
def gerar_resposta(pergunta, contexto):
    time.sleep(1.0) # Simulando geração de texto
    return f"De acordo com a base, a Light atende a zona sul."

# O track_pipeline abraça todos os passos abaixo gerando uma árvore visual
@track_pipeline(run_name="Pergunta_Cliente")
def pipeline_principal(pergunta):
    contexto = buscar_documentos(pergunta)
    resposta = gerar_resposta(pergunta, contexto)
    return resposta

if __name__ == "__main__":
    resposta_final = pipeline_principal("Onde a Light atua?")
    print("Resposta:", resposta_final)
