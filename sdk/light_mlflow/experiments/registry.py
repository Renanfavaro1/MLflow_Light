import mlflow
from mlflow.tracking import MlflowClient
import logging

logger = logging.getLogger("light_mlflow.registry")

class ModelRegistry:
    """
    Utilitário para gerenciar o ciclo de vida dos modelos no Hub do MLflow.
    """
    @staticmethod
    def register_model(run_id: str, artifact_path: str, model_name: str):
        """
        Publica um modelo recém-treinado no Catálogo de Modelos (Registry).
        Isso cria uma nova "versão" para o modelo.
        """
        model_uri = f"runs:/{run_id}/{artifact_path}"
        result = mlflow.register_model(model_uri, model_name)
        logger.info(f"✅ Modelo '{model_name}' publicado com a versão v{result.version}")
        return result

    @staticmethod
    def promote_to_production(model_name: str, version: int):
        """
        Promove um modelo para Produção usando o sistema de 'aliases' do MLflow 2.18+.
        O alias 'champion' indica qual versão é a que está rodando em produção.
        """
        client = MlflowClient()
        client.set_registered_model_alias(
            name=model_name,
            alias="champion",
            version=str(version)
        )
        logger.info(f"🚀 Modelo '{model_name}' v{version} promovido para PRODUÇÃO (alias: @champion)!")

    @staticmethod
    def get_production_model_uri(model_name: str) -> str:
        """
        Retorna a URI do modelo que está em produção para ser usado em inferência.
        """
        return f"models:/{model_name}@champion"

