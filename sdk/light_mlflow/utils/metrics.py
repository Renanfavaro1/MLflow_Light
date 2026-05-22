import mlflow
import logging

logger = logging.getLogger("light_mlflow.metrics")

def log_metrics_dict(metrics_dict: dict, step: int = None):
    """
    Facilita o log de múltiplos indicadores numéricos de uma vez só.
    """
    if mlflow.active_run():
        mlflow.log_metrics(metrics_dict, step=step)
    else:
        logger.warning("Nenhum run ativo. Use @track_run ou start_run() primeiro.")
