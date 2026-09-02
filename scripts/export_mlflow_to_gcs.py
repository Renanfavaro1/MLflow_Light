"""
ETL: MLflow PostgreSQL -> GCS Parquet
=====================================
Exporta todas as tabelas públicas do banco PostgreSQL do MLflow para
arquivos Parquet no Google Cloud Storage, além de gerar uma tabela
consolidada de Traces de IA para consumo direto pelo Databricks / Unity Catalog.

A tabela 'spans' contém textos gigantescos (prompts, respostas de IA,
PDFs codificados). Para evitar Out-of-Memory no Cloud Run (4GB RAM),
a truncagem de texto é feita DENTRO DO SQL (LEFT), antes que o dado
chegue ao driver psycopg2 em Python.
"""

import os
import sys
import logging
import json
import gc
import uuid
import psycopg2
import psycopg2.extras
import pyarrow as pa
import pyarrow.parquet as pq
from google.cloud import storage

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("etl")

DATABASE_URL = os.environ.get("DATABASE_URL", "")
GCS_BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME", "mlflow_stats")
GCS_PREFIX = "mlflow_export/latest"

# Cotação do dólar para conversão dinâmica USD -> BRL
COTACAO_DOLAR = float(os.environ.get("COTACAO_DOLAR", "5.75"))

# Limite de caracteres para colunas de texto no SQL (10 KB por célula)
MAX_TEXT_LEN = 10_000

# Tabelas pesadas que precisam de tratamento especial (textos gigantes)
HEAVY_TABLES = {"spans", "inputs", "trace_info"}

# Batch sizes
BATCH_HEAVY = 100   # 100 linhas por vez para tabelas com payloads enormes
BATCH_NORMAL = 5000 # 5000 linhas por vez para tabelas leves


def get_connection():
    """Cria conexão direta com psycopg2 (sem SQLAlchemy)."""
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL não definida.")
    return psycopg2.connect(DATABASE_URL)


def get_public_tables(conn):
    """Lista todas as tabelas do schema public (exceto alembic)."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_type = 'BASE TABLE'
              AND table_name != 'alembic_version'
            ORDER BY table_name
        """)
        return [row[0] for row in cur.fetchall()]


def get_text_columns(conn, table_name):
    """Identifica colunas de tipo texto/bytea na tabela (candidatas a truncagem)."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = %s
              AND data_type IN ('text', 'character varying', 'bytea', 'json', 'jsonb')
            ORDER BY ordinal_position
        """, (table_name,))
        return {row[0]: row[1] for row in cur.fetchall()}


def get_all_columns(conn, table_name):
    """Retorna todas as colunas da tabela na ordem original."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = %s
            ORDER BY ordinal_position
        """, (table_name,))
        return [row[0] for row in cur.fetchall()]


def build_select_query(conn, table_name, truncate_text=False):
    """
    Constrói a query SELECT. Se truncate_text=True, envolve colunas
    de texto com LEFT(col::text, MAX_TEXT_LEN) diretamente no SQL.
    Isso garante que o driver psycopg2 NUNCA receba strings gigantes.
    """
    all_cols = get_all_columns(conn, table_name)
    if not truncate_text:
        return f"SELECT * FROM {table_name}", all_cols

    text_cols = get_text_columns(conn, table_name)
    projections = []
    for col in all_cols:
        if col in text_cols:
            # Trunca no banco: o dado já chega cortado ao Python
            projections.append(f"LEFT({col}::text, {MAX_TEXT_LEN}) AS {col}")
        else:
            projections.append(col)

    return f"SELECT {', '.join(projections)} FROM {table_name}", all_cols


def get_row_count(conn, table_name):
    """Conta registros na tabela."""
    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM {table_name}")
        return cur.fetchone()[0]


def make_arrow_schema(columns, sample_rows):
    """
    Cria um schema PyArrow a partir de uma amostra de dados.
    Força colunas totalmente nulas para pa.string() para evitar pa.null().
    """
    col_data = {col: [] for col in columns}
    for row in sample_rows:
        for i, col in enumerate(columns):
            val = row[i]
            if isinstance(val, (dict, list)):
                val = json.dumps(val, ensure_ascii=False)
            elif isinstance(val, bytes):
                val = val.decode("utf-8", errors="replace")
            elif isinstance(val, memoryview):
                val = bytes(val).decode("utf-8", errors="replace")
            col_data[col].append(val)

    table = pa.table(col_data)
    fields = []
    for field in table.schema:
        if field.type == pa.null():
            fields.append(pa.field(field.name, pa.string()))
        else:
            fields.append(field)
    return pa.schema(fields)


def rows_to_arrow_table(columns, rows, schema):
    """Converte lista de tuplas (rows) em pa.Table alinhada ao schema."""
    col_data = {col: [] for col in columns}
    for row in rows:
        for i, col in enumerate(columns):
            val = row[i]
            if isinstance(val, (dict, list)):
                val = json.dumps(val, ensure_ascii=False)
            elif isinstance(val, bytes):
                val = bytes(val).decode("utf-8", errors="replace")
            elif isinstance(val, memoryview):
                val = bytes(val).decode("utf-8", errors="replace")
            col_data[col].append(val)

    table = pa.table(col_data)
    try:
        return table.cast(schema, safe=False)
    except Exception:
        return table


def export_table(conn, table_name, bucket_name, prefix):
    """
    Exporta uma tabela individual para Parquet no GCS usando server-side cursor.
    """
    is_heavy = table_name in HEAVY_TABLES
    batch_size = BATCH_HEAVY if is_heavy else BATCH_NORMAL
    temp_file = f"/tmp/{table_name}.parquet"

    if os.path.exists(temp_file):
        os.remove(temp_file)

    total = get_row_count(conn, table_name)
    if total == 0:
        logger.info(f"  {table_name}: vazia, pulando.")
        return False

    logger.info(f"  {table_name}: {total} registros (batch={batch_size}, heavy={is_heavy})")

    select_sql, columns = build_select_query(conn, table_name, truncate_text=is_heavy)

    writer = None
    schema = None
    total_rows = 0

    try:
        cursor_name = f"etl_{table_name}_{uuid.uuid4().hex[:8]}"
        with conn.cursor(name=cursor_name) as cur:
            cur.itersize = batch_size
            cur.execute(select_sql)

            while True:
                rows = cur.fetchmany(batch_size)
                if not rows:
                    break

                if schema is None:
                    schema = make_arrow_schema(columns, rows)
                    writer = pq.ParquetWriter(temp_file, schema, compression="snappy")

                arrow_table = rows_to_arrow_table(columns, rows, schema)
                writer.write_table(arrow_table)
                total_rows += len(rows)

                if total_rows % 2500 < batch_size or total_rows <= batch_size:
                    logger.info(f"    {table_name}: {total_rows}/{total} linhas...")

                del rows, arrow_table
                gc.collect()

        if writer:
            writer.close()
            writer = None

        logger.info(f"  Upload: {table_name}.parquet ({total_rows} registros)...")
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(f"{prefix}/{table_name}.parquet")
        blob.upload_from_filename(temp_file)

        if table_name == "latest_metrics":
            bucket.blob(f"{prefix}/metrics_latest.parquet").upload_from_filename(temp_file)

        logger.info(f"  ✅ {table_name}: {total_rows} registros exportados com sucesso.")
        return True

    except Exception as e:
        logger.error(f"  ❌ Erro em {table_name}: {e}")
        return False

    finally:
        if writer:
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


def export_consolidated_traces(conn, bucket_name, prefix, cotacao_dolar=5.75):
    """
    Gera e exporta a tabela consolidada de Traces de IA unindo:
    trace_info + experiments + trace_tags + trace_request_metadata
    Calcula automaticamente tokens, latência, status, custo em USD e BRL.
    """
    logger.info("=" * 70)
    logger.info(f"Gerando visualização consolidada de Traces (Cotação Dólar: R$ {cotacao_dolar:.2f})...")
    
    query = f"""
    SELECT 
        t.request_id AS trace_id,
        t.experiment_id,
        COALESCE(e.name, 'Sem Experimento') AS experiment_name,
        COALESCE(tag_service.value, e.name, 'Agente Desconhecido') AS service_name,
        TO_TIMESTAMP(t.timestamp_ms / 1000.0) AS data_hora_atendimento,
        (t.execution_time_ms / 1000.0) AS latencia_segundos,
        t.status,
        
        -- Contagem de Tokens
        COALESCE(CAST(NULLIF(meta_prompt.value, '') AS INTEGER), 0) AS prompt_tokens,
        COALESCE(CAST(NULLIF(meta_comp.value, '') AS INTEGER), 0) AS completion_tokens,
        COALESCE(CAST(NULLIF(meta_total.value, '') AS INTEGER), 0) AS total_tokens,
        
        -- Custos
        COALESCE(CAST(NULLIF(meta_cost.value, '') AS NUMERIC(10, 6)), 0.0) AS custo_usd,
        ROUND(COALESCE(CAST(NULLIF(meta_cost.value, '') AS NUMERIC(10, 6)), 0.0) * {cotacao_dolar}, 4) AS custo_brl

    FROM trace_info t
    LEFT JOIN experiments e 
        ON t.experiment_id = CAST(e.experiment_id AS VARCHAR)
    LEFT JOIN trace_tags tag_service 
        ON t.request_id = tag_service.request_id 
        AND tag_service.key = 'service.name'
    LEFT JOIN trace_request_metadata meta_prompt 
        ON t.request_id = meta_prompt.request_id 
        AND meta_prompt.key = 'mlflow.trace.prompt_tokens'
    LEFT JOIN trace_request_metadata meta_comp 
        ON t.request_id = meta_comp.request_id 
        AND meta_comp.key = 'mlflow.trace.completion_tokens'
    LEFT JOIN trace_request_metadata meta_total 
        ON t.request_id = meta_total.request_id 
        AND meta_total.key = 'mlflow.trace.total_tokens'
    LEFT JOIN trace_request_metadata meta_cost 
        ON t.request_id = meta_cost.request_id 
        AND meta_cost.key = 'mlflow.trace.cost'
    ORDER BY t.timestamp_ms DESC;
    """

    temp_file = "/tmp/traces_consolidated.parquet"
    if os.path.exists(temp_file):
        os.remove(temp_file)

    try:
        with conn.cursor() as cur:
            cur.execute(query)
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()

        if not rows:
            logger.info("  Nenhum trace encontrado para consolidar.")
            return False

        logger.info(f"  Consolidados {len(rows)} traces com sucesso.")
        schema = make_arrow_schema(columns, rows)
        arrow_table = rows_to_arrow_table(columns, rows, schema)
        pq.write_table(arrow_table, temp_file, compression="snappy")

        # Upload no GCS
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(f"{prefix}/traces_consolidated.parquet")
        blob.upload_from_filename(temp_file)

        # Alias para compatibilidade
        bucket.blob(f"{prefix}/tb_traces_consolidated.parquet").upload_from_filename(temp_file)

        logger.info("  ✅ Tabela consolidada enviada para GCS: traces_consolidated.parquet")
        return True

    except Exception as e:
        logger.error(f"  ❌ Erro ao consolidar traces: {e}")
        return False
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)
        gc.collect()


def main():
    logger.info("=" * 70)
    logger.info("ETL MLflow PostgreSQL -> GCS Parquet (com Traces & Spans)")
    logger.info("=" * 70)

    conn = get_connection()
    conn.set_session(readonly=True, autocommit=True)

    try:
        tables = get_public_tables(conn)
        logger.info(f"Encontradas {len(tables)} tabelas: {', '.join(tables)}")

        # Processa tabelas pesadas PRIMEIRO (quando a RAM está mais limpa)
        heavy_first = sorted(tables, key=lambda t: (t not in HEAVY_TABLES, t))

        exported = 0
        for table in heavy_first:
            ok = export_table(conn, table, GCS_BUCKET_NAME, GCS_PREFIX)
            if ok:
                exported += 1

        # Gera também a visualização consolidada de Traces de IA
        export_consolidated_traces(conn, GCS_BUCKET_NAME, GCS_PREFIX, cotacao_dolar=COTACAO_DOLAR)

        logger.info("=" * 70)
        logger.info(f"✅ Pipeline concluído: {exported}/{len(tables)} tabelas exportadas + visão consolidada gerada.")
        logger.info("=" * 70)

    except Exception as e:
        logger.error(f"Falha crítica: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
