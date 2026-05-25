import os
import mlflow
import logging
import warnings
import urllib3

# Suprime os avisos de conexão insegura gerados pelo proxy corporativo
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("light_mlflow")

class LightMLflowConfig:
    """
    Classe utilitária para configurar a conexão com o MLflow Tracking Server da Light.
    """
    @staticmethod
    def setup(tracking_uri: str = None, experiment_name: str = "Default"):
        """
        Configura o ambiente do MLflow.
        Se tracking_uri não for passado, tentará ler da variável de ambiente MLFLOW_TRACKING_URI.
        """
        uri = tracking_uri or os.environ.get("MLFLOW_TRACKING_URI")
        
        if uri:
            mlflow.set_tracking_uri(uri)
            logger.info(f"✅ MLflow Tracking URI configurado para: {uri}")
        else:
            logger.warning("⚠️ MLFLOW_TRACKING_URI não definido. O MLflow usará o armazenamento local (pasta mlruns/).")

        # Define o experimento ativo. Se não existir, o MLflow cria automaticamente.
        mlflow.set_experiment(experiment_name)
        logger.info(f"✅ Experimento ativo: {experiment_name}")

    @staticmethod
    def get_current_run_id() -> str:
        """Retorna o ID do run atual, se existir."""
        active_run = mlflow.active_run()
        return active_run.info.run_id if active_run else None
