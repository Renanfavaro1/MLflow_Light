import os
import logging
import json
from datetime import datetime
import pandas as pd
from sqlalchemy import create_engine, text
from google.cloud import storage

# --- Configurações de Log ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Configurações (Ambiente) ---
DATABASE_URL = os.environ.get("DATABASE_URL")
GCS_BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME", "mlflow_stats") 

def get_db_engine():
    """Cria a conexão com o banco PostgreSQL do MLflow."""
    if not DATABASE_URL:
        raise ValueError("A variável de ambiente DATABASE_URL não está definida.")
    return create_engine(DATABASE_URL)

def get_all_public_tables(engine):
    """Descobre dinamicamente todas as tabelas do schema public do PostgreSQL."""
    query = """
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public' 
      AND table_type = 'BASE TABLE'
      AND table_name != 'alembic_version'
    ORDER BY table_name;
    """
    with engine.connect() as conn:
        df_tables = pd.read_sql_query(text(query), conn)
    return df_tables['table_name'].tolist()

def extract_table_to_df(engine, table_name, query=None):
    """Extrai dados de uma tabela específica ou usando uma query."""
    logger.info(f"Extraindo dados de: {table_name}...")
    try:
        if query:
            df = pd.read_sql_query(text(query), engine)
        else:
            df = pd.read_sql_table(table_name, engine)
        logger.info(f"Extração concluída para {table_name}. Linhas: {len(df)}")
        return df
    except Exception as e:
        logger.error(f"Erro ao extrair {table_name}: {e}")
        return pd.DataFrame()

def sanitize_df_for_parquet(df):
    """Garante que colunas com estruturas complexas (dicts/listas/JSON) sejam serializadas sem erro no PyArrow."""
    for col in df.columns:
        if df[col].dtype == 'object':
            first_valid = df[col].dropna().iloc[0] if not df[col].dropna().empty else None
            if isinstance(first_valid, (dict, list)):
                df[col] = df[col].apply(lambda x: json.dumps(x, ensure_ascii=False) if isinstance(x, (dict, list)) else (str(x) if x is not None else None))
    return df

def save_df_to_gcs_parquet(df, bucket_name, destination_blob_name):
    """Salva o DataFrame como Parquet diretamente no GCS."""
    if df.empty:
        logger.info(f"DataFrame vazio. Pulando upload para {destination_blob_name}.")
        return

    logger.info(f"Iniciando upload de Parquet para gs://{bucket_name}/{destination_blob_name}...")
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)

        temp_file = f"/tmp/{destination_blob_name.split('/')[-1]}"
        
        # Sanitiza tipos complexos antes de salvar
        df_sanitized = sanitize_df_for_parquet(df.copy())
        df_sanitized.to_parquet(temp_file, index=False)
        
        blob.upload_from_filename(temp_file)
        
        if os.path.exists(temp_file):
            os.remove(temp_file)
            
        logger.info(f"Upload concluído: gs://{bucket_name}/{destination_blob_name} ({len(df)} registros)")
    except Exception as e:
        logger.error(f"Erro ao fazer upload para o GCS ({destination_blob_name}): {e}")
        raise

def main():
    logger.info("Iniciando processo de ETL Dinâmico: MLflow (PostgreSQL) -> GCS (Parquet)")
    
    try:
        engine = get_db_engine()
        prefix = "mlflow_export/latest"
        
        # 1. Descobre dinamicamente todas as tabelas públicas do MLflow
        tables = get_all_public_tables(engine)
        logger.info(f"Identificadas {len(tables)} tabelas no schema public: {', '.join(tables)}")

        # 2. Extração e Carga de cada tabela
        exported_count = 0
        for table in tables:
            df = extract_table_to_df(engine, table)
            if not df.empty:
                save_df_to_gcs_parquet(df, GCS_BUCKET_NAME, f"{prefix}/{table}.parquet")
                exported_count += 1
                
                # Para manter total compatibilidade com queries existentes que buscam 'metrics_latest.parquet'
                if table == "latest_metrics":
                    save_df_to_gcs_parquet(df, GCS_BUCKET_NAME, f"{prefix}/metrics_latest.parquet")

        logger.info(f"Pipeline ETL finalizado com sucesso! {exported_count}/{len(tables)} tabelas com dados exportadas para gs://{GCS_BUCKET_NAME}/{prefix}/")

    except Exception as e:
        logger.error(f"Falha na execução do pipeline: {e}")
        raise

if __name__ == "__main__":
    main()
