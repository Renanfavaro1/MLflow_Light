import os
import logging
import json
import gc
from datetime import datetime
import pandas as pd
from sqlalchemy import create_engine, text
from google.cloud import storage
import pyarrow as pa
import pyarrow.parquet as pq

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

def sanitize_df_for_parquet(df, max_str_len=30000):
    """Garante que colunas complexas sejam strings consistentes e trunca payloads gigantes (base64/arquivos)."""
    for col in df.columns:
        if df[col].dtype == 'object':
            def clean_val(x):
                if x is None:
                    return None
                if isinstance(x, (dict, list)):
                    s = json.dumps(x, ensure_ascii=False)
                elif isinstance(x, bytes):
                    s = x.decode('utf-8', errors='replace')
                else:
                    s = str(x)
                
                # Trunca strings anômalas (ex: imagens base64 ou PDFs inteiros) para no máximo 30KB
                if len(s) > max_str_len:
                    return s[:max_str_len] + "... [TRUNCATED]"
                return s

            df[col] = df[col].apply(clean_val).astype('string')
    return df

def extract_and_export_table(engine, table_name, bucket_name, prefix, default_batch=1000):
    """Extrai dados com paginação nativa SQL e grava incrementalmente no Parquet."""
    temp_file = f"/tmp/{table_name}.parquet"
    
    if os.path.exists(temp_file):
        try:
            os.remove(temp_file)
        except Exception:
            pass

    # Para tabelas muito pesadas como spans, usa lotes menores de 250 registros
    batch_size = 250 if table_name in ("spans", "inputs", "trace_info") else default_batch
    writer = None
    offset = 0
    total_rows = 0

    try:
        # 1. Conta o total de registros na tabela
        with engine.connect() as conn:
            count_query = text(f"SELECT COUNT(*) FROM {table_name}")
            total_in_db = conn.execute(count_query).scalar() or 0

        if total_in_db == 0:
            logger.info(f"Tabela '{table_name}' vazia. Pulando.")
            return False

        logger.info(f"Extraindo {total_in_db} registros de {table_name} em lotes de {batch_size}...")

        # 2. Paginação SQL real no PostgreSQL (Zero acúmulo de buffer em RAM)
        writer_schema = None
        while offset < total_in_db:
            page_query = text(f"SELECT * FROM {table_name} LIMIT {batch_size} OFFSET {offset}")
            with engine.connect() as conn:
                chunk = pd.read_sql_query(page_query, conn)

            if chunk.empty:
                break

            # Sanitiza e limita tamanho de strings gigantescas
            chunk_sanitized = sanitize_df_for_parquet(chunk)
            table_arrow = pa.Table.from_pandas(chunk_sanitized, preserve_index=False)

            # Inicializa o escritor Parquet no primeiro lote
            if writer is None:
                fields = []
                for field in table_arrow.schema:
                    if field.type == pa.null():
                        fields.append(pa.field(field.name, pa.string()))
                    else:
                        fields.append(field)
                writer_schema = pa.schema(fields)
                writer = pq.ParquetWriter(temp_file, writer_schema, compression='snappy')

            try:
                table_to_write = table_arrow.cast(writer_schema, safe=False)
            except Exception:
                table_to_write = table_arrow

            writer.write_table(table_to_write)
            total_rows += len(chunk)
            offset += batch_size

            if total_rows % 2500 == 0 or total_rows < 1000 or total_rows >= total_in_db:
                logger.info(f"Progresso {table_name}: {total_rows}/{total_in_db} linhas...")

            # Libera memória imediatamente
            del chunk
            del chunk_sanitized
            del table_arrow
            gc.collect()

        if writer is not None:
            writer.close()
            writer = None

        if total_rows > 0:
            logger.info(f"Fazendo upload para o GCS: {table_name}.parquet ({total_rows} registros)...")
            storage_client = storage.Client()
            bucket = storage_client.bucket(bucket_name)
            
            blob = bucket.blob(f"{prefix}/{table_name}.parquet")
            blob.upload_from_filename(temp_file)
            
            # Compatibilidade legada para o Databricks
            if table_name == "latest_metrics":
                blob_compat = bucket.blob(f"{prefix}/metrics_latest.parquet")
                blob_compat.upload_from_filename(temp_file)
                
            logger.info(f"✅ Upload concluído com sucesso: gs://{bucket_name}/{prefix}/{table_name}.parquet ({total_rows} registros)")
            return True
        else:
            return False

    except Exception as e:
        logger.error(f"⚠️ Aviso: Falha ao exportar tabela '{table_name}': {e}")
        return False
    finally:
        if writer is not None:
            try:
                writer.close()
            except Exception:
                pass
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except Exception:
                pass
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
