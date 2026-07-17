import os
import logging
from datetime import datetime
import pandas as pd
from sqlalchemy import create_engine
from google.cloud import storage

# --- Configurações de Log ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Configurações (Ambiente) ---
# Em produção (ex: Cloud Run/Job), essas variáveis devem vir do ambiente
DATABASE_URL = os.environ.get("DATABASE_URL")
GCS_BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME", "mlflow_stats") 
# Opcional: Se for rodar local com service account key file
# os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/caminho/para/key.json"

def get_db_engine():
    """Cria a conexão com o banco PostgreSQL do MLflow."""
    if not DATABASE_URL:
        raise ValueError("A variável de ambiente DATABASE_URL não está definida.")
    # Exemplo: postgresql://user:password@host:port/dbname
    return create_engine(DATABASE_URL)

def extract_table_to_df(engine, table_name, query=None):
    """Extrai dados de uma tabela específica ou usando uma query."""
    logger.info(f"Extraindo dados de: {table_name}...")
    try:
        if query:
            df = pd.read_sql_query(query, engine)
        else:
            df = pd.read_sql_table(table_name, engine)
        logger.info(f"Extração concluída para {table_name}. Linhas: {len(df)}")
        return df
    except Exception as e:
        logger.error(f"Erro ao extrair {table_name}: {e}")
        return pd.DataFrame()

def save_df_to_gcs_parquet(df, bucket_name, destination_blob_name):
    """Salva o DataFrame como Parquet diretamente no GCS."""
    if df.empty:
        logger.warning(f"DataFrame vazio. Pulando upload para {destination_blob_name}.")
        return

    logger.info(f"Iniciando upload de Parquet para gs://{bucket_name}/{destination_blob_name}...")
    try:
        # Inicializa cliente do Storage
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)

        # O Pandas consegue salvar direto no GCS se o pacote gcsfs estiver instalado,
        # mas fazer via memória garante não criar arquivos locais soltos.
        
        # Salva o dataframe em um arquivo parquet temporário local
        temp_file = f"/tmp/{destination_blob_name.split('/')[-1]}"
        df.to_parquet(temp_file, index=False)
        
        # Upload para o GCS
        blob.upload_from_filename(temp_file)
        
        # Remove temporário
        if os.path.exists(temp_file):
            os.remove(temp_file)
            
        logger.info(f"Upload concluído com sucesso: gs://{bucket_name}/{destination_blob_name}")
    except Exception as e:
        logger.error(f"Erro ao fazer upload para o GCS: {e}")
        raise

def main():
    logger.info("Iniciando processo de ETL: MLflow (PostgreSQL) -> GCS (Parquet)")
    
    try:
        engine = get_db_engine()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = f"mlflow_export/date={datetime.now().strftime('%Y%m%d')}/run_{timestamp}"
        
        # 1. Extração: Experimentos
        df_experiments = extract_table_to_df(engine, "experiments")
        
        # 2. Extração: Runs
        df_runs = extract_table_to_df(engine, "runs")
        
        # 3. Extração: Métricas
        # Dica: Na tabela metrics do MLflow, pode haver um grande volume de dados se logar a cada step.
        # Para analytics, muitas vezes queremos apenas o último valor de cada métrica por run.
        metrics_query = """
        SELECT m.* 
        FROM metrics m
        INNER JOIN (
            SELECT run_uuid, key, MAX(timestamp) as max_time
            FROM metrics
            GROUP BY run_uuid, key
        ) latest ON m.run_uuid = latest.run_uuid AND m.key = latest.key AND m.timestamp = latest.max_time;
        """
        df_metrics_latest = extract_table_to_df(engine, "metrics_latest", query=metrics_query)
        
        # 4. Extração: Params
        df_params = extract_table_to_df(engine, "params")
        
        # 5. Extração: Tags (Opcional, mas útil)
        df_tags = extract_table_to_df(engine, "tags")

        # --- Transformação & Carga (Upload para GCS) ---
        # Salvamos particionado pela data de extração para facilitar a leitura no Databricks
        
        save_df_to_gcs_parquet(df_experiments, GCS_BUCKET_NAME, f"{prefix}/experiments.parquet")
        save_df_to_gcs_parquet(df_runs, GCS_BUCKET_NAME, f"{prefix}/runs.parquet")
        save_df_to_gcs_parquet(df_metrics_latest, GCS_BUCKET_NAME, f"{prefix}/metrics_latest.parquet")
        save_df_to_gcs_parquet(df_params, GCS_BUCKET_NAME, f"{prefix}/params.parquet")
        save_df_to_gcs_parquet(df_tags, GCS_BUCKET_NAME, f"{prefix}/tags.parquet")

        logger.info("Pipeline ETL finalizado com sucesso!")

    except Exception as e:
        logger.error(f"Falha na execução do pipeline: {e}")

if __name__ == "__main__":
    main()
