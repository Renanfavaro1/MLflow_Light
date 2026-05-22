import mlflow
import logging

logger = logging.getLogger("light_mlflow.artifacts")

def log_plot(fig, artifact_path: str):
    """
    Salva diretamente uma figura gerada (Matplotlib, Plotly) como arquivo no GCS.
    Isso evita que o cientista precise salvar o arquivo ".png" no disco antes de mandar pro MLflow.
    """
    if mlflow.active_run():
        mlflow.log_figure(fig, artifact_path)
    else:
        logger.warning("Nenhum run ativo. O gráfico não foi salvo.")

def log_json_dict(data: dict, file_name: str):
    """
    Salva um dicionário python como um arquivo JSON nos artefatos.
    Útil para salvar configurações longas, respostas brutas de API, etc.
    """
    if mlflow.active_run():
        mlflow.log_dict(data, file_name)
    else:
        logger.warning("Nenhum run ativo. O JSON não foi salvo.")
