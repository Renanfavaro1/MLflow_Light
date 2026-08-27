import os
import logging
import json
import gc
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
    return create_engine(DATABASE_URL, pool_pre_ping=True)

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

def sanitize_df_for_parquet(df):
    """Garante que colunas com estruturas complexas (dicts/listas/JSON) sejam serializadas sem erro no PyArrow."""
    for col in df.columns:
        if df[col].dtype == 'object':
            first_valid = df[col].dropna().iloc[0] if not df[col].dropna().empty else None
            if isinstance(first_valid, (dict, list)):
                df[col] = df[col].apply(lambda x: json.dumps(x, ensure_ascii=False) if isinstance(x, (dict, list)) else (str(x) if x is not None else None))
            elif isinstance(first_valid, bytes):
                df[col] = df[col].apply(lambda x: "<bytes>" if x is not None else None)
    return df

def save_df_to_gcs_parquet(df, bucket_name, destination_blob_name):
    """Salva o DataFrame como Parquet diretamente no GCS liberando arquivos temporários."""
    if df.empty:
        return

    logger.info(f"Iniciando upload de Parquet para gs://{bucket_name}/{destination_blob_name} ({len(df)} registros)...")
    temp_file = f"/tmp/{destination_blob_name.split('/')[-1]}"
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)

        # Sanitiza tipos complexos antes de salvar
        df_sanitized = sanitize_df_for_parquet(df)
        df_sanitized.to_parquet(temp_file, index=False, compression='snappy')
        
        blob.upload_from_filename(temp_file)
        logger.info(f"Upload concluído: gs://{bucket_name}/{destination_blob_name} ({len(df)} registros)")
    except Exception as e:
        logger.error(f"Erro ao fazer upload para o GCS ({destination_blob_name}): {e}")
    finally:
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except Exception:
                pass

def extract_and_export_table(engine, table_name, bucket_name, prefix):
    """Extrai uma tabela do banco e exporta para o GCS com baixo consumo de memória."""
    logger.info(f"Extraindo dados de: {table_name}...")
    try:
        # Se for a tabela pesada de spans ou metrics, lê e grava de forma otimizada
        query = text(f"SELECT * FROM {table_name}")
        df = pd.read_sql_query(query, engine)
        
        row_count = len(df)
        logger.info(f"Extração concluída para {table_name}. Linhas: {row_count}")
        
        if row_count > 0:
            save_df_to_gcs_parquet(df, bucket_name, f"{prefix}/{table_name}.parquet")
            
            # Compatibilidade com queries legadas do Databricks
            if table_name == "latest_metrics":
                save_df_to_gcs_parquet(df, bucket_name, f"{prefix}/metrics_latest.parquet")
            
            return True
        else:
            logger.info(f"Tabela '{table_name}' vazia. Pulando upload.")
            return False
            
    except Exception as e:
        logger.error(f"⚠️ Aviso: Falha ao processar tabela '{table_name}': {e}")
        return False
    finally:
        # Força liberação de memória RAM para evitar Out-Of-Memory (OOM)
        if 'df' in locals():
            del df
        gc.collect()

def main():
    logger.info("Iniciando processo de ETL Otimizado: MLflow (PostgreSQL) -> GCS (Parquet)")
    
    try:
        engine = get_db_engine()
        prefix = "mlflow_export/latest"
        
        # 1. Descobre dinamicamente todas as tabelas públicas do MLflow
        tables = get_all_public_tables(engine)
        logger.info(f"Identificadas {len(tables)} tabelas no schema public: {', '.join(tables)}")

        # 2. Extração e Carga resiliente de cada tabela
        exported_count = 0
        for table in tables:
            exported = extract_and_export_table(engine, table, GCS_BUCKET_NAME, prefix)
            if exported:
                exported_count += 1

        logger.info(f"✅ Pipeline ETL finalizado com sucesso! {exported_count} tabelas com dados exportadas para gs://{GCS_BUCKET_NAME}/{prefix}/")

    except Exception as e:
        logger.error(f"Falha crítica na execução do pipeline: {e}")
        raise

if __name__ == "__main__":
    main()
