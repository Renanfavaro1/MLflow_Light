import os
import time
import mlflow
import logging
import warnings
import urllib3
from typing import Optional

# Suprime os avisos de conexão insegura gerados pelo proxy corporativo
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("light_mlflow")

_cached_token = None
_token_expiry = 0

def get_google_id_token(audience: str) -> Optional[str]:
    """
    Obtém o Google ID Token automaticamente do Metadata Server do Cloud Run ou do ambiente.
    """
    global _cached_token, _token_expiry

    if not audience:
        return None

    # 1. Se já fornecido manualmente via variável de ambiente
    if os.environ.get("MLFLOW_TRACKING_TOKEN"):
        return os.environ.get("MLFLOW_TRACKING_TOKEN")

    now = time.time()
    if _cached_token and _token_expiry > now + 300:
        return _cached_token

    clean_aud = audience.rstrip('/')

    # 2. Tentar via google-auth oficial (se biblioteca estiver instalada)
    try:
        import google.auth.transport.requests
        import google.oauth2.id_token
        auth_req = google.auth.transport.requests.Request()
        token = google.oauth2.id_token.fetch_id_token(auth_req, clean_aud)
        if token:
            _cached_token = token
            _token_expiry = now + 3000 # Cache de 50 minutos
            return _cached_token
    except Exception:
        pass

    # 3. Fallback direto no Metadata Server do GCP (Cloud Run / Compute Engine)
    try:
        import urllib.request
        meta_url = f"http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity?audience={clean_aud}"
        req = urllib.request.Request(meta_url, headers={"Metadata-Flavor": "Google"})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            token = resp.read().decode('utf-8').strip()
            if token:
                _cached_token = token
                _token_expiry = now + 3000
                return _cached_token
    except Exception:
        pass

    return None

class LightMLflowConfig:
    """
    Classe utilitária para configurar a conexão com o MLflow Tracking Server da Light.
    """
    @staticmethod
    def setup(tracking_uri: str = None, experiment_name: str = "Default"):
        """
        Configura o ambiente do MLflow.
        Se tracking_uri não for passado, tentará ler da variável de ambiente MLFLOW_TRACKING_URI.
        Nunca interrompe a inicialização da aplicação em caso de falha de conexão ou 401/403.
        """
        try:
            # Configuração nativa de retentativas do MLflow para Alta Concorrência
            if not os.environ.get("MLFLOW_HTTP_REQUEST_MAX_RETRIES"):
                os.environ["MLFLOW_HTTP_REQUEST_MAX_RETRIES"] = "5"

            uri = tracking_uri or os.environ.get("MLFLOW_TRACKING_URI")
            
            if uri:
                mlflow.set_tracking_uri(uri)
                logger.info(f"✅ MLflow Tracking URI configurado para: {uri}")

                # Se houver token estático configurado, usa diretamente
                static_token = os.environ.get("MLFLOW_TRACKING_TOKEN")
                if not static_token:
                    # Resolve automaticamente o Google ID Token se rodando no Cloud Run
                    token = get_google_id_token(uri)
                    if token:
                        os.environ["MLFLOW_TRACKING_TOKEN"] = token
                        logger.info("🔑 Google ID Token obtido automaticamente para a Service Account.")
            else:
                logger.warning("⚠️ MLFLOW_TRACKING_URI não definido. O MLflow usará o armazenamento local (pasta mlruns/).")

            # Define o experimento ativo. Se não existir ou falhar a conexão, não quebra a aplicação.
            try:
                mlflow.set_experiment(experiment_name)
                logger.info(f"✅ Experimento ativo: {experiment_name}")
            except Exception as exp_err:
                logger.warning(f"⚠️ Não foi possível definir o experimento '{experiment_name}' no MLflow: {exp_err}. A aplicação continuará normalmente.")

        except Exception as e:
            logger.warning(f"⚠️ Aviso: Falha na inicialização do MLflow: {e}. A aplicação prosseguirá normalmente sem telemetria.")

    @staticmethod
    def get_current_run_id() -> str:
        """Retorna o ID do run atual, se existir."""
        try:
            active_run = mlflow.active_run()
            return active_run.info.run_id if active_run else None
        except Exception:
            return None
