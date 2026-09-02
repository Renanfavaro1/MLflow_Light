"""
ETL: MLflow PostgreSQL -> GCS Parquet (com Traces, Spans e Assessments)
======================================================================
Exporta todas as tabelas públicas do banco PostgreSQL do MLflow (incluindo
as tabelas de Traces de IA e Assessments do LLM Judge) para arquivos Parquet no GCS.

Garante escape de palavras reservadas no SQL ("key", "value", "user", etc.)
e gera a tabela consolidada de Traces de IA ('traces_consolidated.parquet')
com cálculo dinâmico de custo em Reais (BRL).
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

# Limite de caracteres para colunas de texto pesado (10 KB por célula)
MAX_TEXT_LEN = 10_000

# Tabelas com payloads textuais grandes que recebem truncagem segura no SQL
HEAVY_TABLES = {"spans", "inputs", "assessments"}

# Batch sizes otimizados
BATCH_HEAVY = 500    # 500 linhas por batch para tabelas pesadas
BATCH_NORMAL = 10000 # 10.000 linhas por batch para tabelas normais


def get_connection():
    """Cria conexão direta com psycopg2 (sem SQLAlchemy)."""
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL não definida.")
    return psycopg2.connect(DATABASE_URL)


def get_public_tables(conn):
    """Lista todas as tabelas do schema public (exceto alembic_version)."""
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
    """Identifica colunas de tipo texto/bytea/json na tabela."""
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
    Constrói a query SELECT escapando identificadores com aspas duplas ("key", "value", etc.).
    Trunca textos pesados se solicitado.
    """
    all_cols = get_all_columns(conn, table_name)
    if not truncate_text:
        quoted_cols = [f'"{col}"' for col in all_cols]
        return f'SELECT {", ".join(quoted_cols)} FROM "{table_name}"', all_cols

    text_cols = get_text_columns(conn, table_name)
    projections = []
    for col in all_cols:
        if col in text_cols:
            projections.append(f'LEFT("{col}"::text, {MAX_TEXT_LEN}) AS "{col}"')
        else:
            projections.append(f'"{col}"')

    return f'SELECT {", ".join(projections)} FROM "{table_name}"', all_cols


def get_row_count(conn, table_name):
    """Conta registros na tabela de forma segura contra palavras reservadas."""
    with conn.cursor() as cur:
        cur.execute(f'SELECT COUNT(*) FROM "{table_name}"')
        return cur.fetchone()[0]


def sanitize_value(val):
    """Converte tipos especiais (dict, list, memoryview, bytes) em tipos serializáveis."""
    if val is None:
        return None
    if isinstance(val, (dict, list)):
        return json.dumps(val, ensure_ascii=False)
    if isinstance(val, (bytes, memoryview)):
        return bytes(val).decode("utf-8", errors="replace")
    return val


def rows_to_pydict_list(columns, rows):
    """Converte tuplas do psycopg2 em lista de dicionários higienizados."""
    dict_rows = []
    for row in rows:
        row_dict = {}
        for col, val in zip(columns, row):
            row_dict[col] = sanitize_value(val)
        dict_rows.append(row_dict)
    return dict_rows


def export_table(conn, table_name, bucket_name, prefix):
    """
    Exporta uma tabela para Parquet no GCS.
    Escapa palavras reservadas do PostgreSQL ("key", "value", etc.) e garante
    que tabelas vazias gerem arquivo Parquet estruturado para o Databricks Unity Catalog.
    """
    is_heavy = table_name in HEAVY_TABLES
    batch_size = BATCH_HEAVY if is_heavy else BATCH_NORMAL
    temp_file = f"/tmp/{table_name}.parquet"

    if os.path.exists(temp_file):
        os.remove(temp_file)

    try:
        total = get_row_count(conn, table_name)
        select_sql, columns = build_select_query(conn, table_name, truncate_text=is_heavy)

        # Caso 1: Tabela vazia -> Gera Parquet estruturado (0 linhas) para o Databricks
        if total == 0:
            logger.info(f"  {table_name}: vazia (0 registros). Gerando Parquet estruturado para Unity Catalog...")
            empty_data = {col: pa.array([], type=pa.string()) for col in columns}
            empty_table = pa.Table.from_pydict(empty_data)
            pq.write_table(empty_table, temp_file, compression="snappy")
            
            client = storage.Client()
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(f"{prefix}/{table_name}.parquet")
            blob.upload_from_filename(temp_file)
            
            if table_name == "latest_metrics":
                bucket.blob(f"{prefix}/metrics_latest.parquet").upload_from_filename(temp_file)
                
            logger.info(f"  ✅ {table_name}: Parquet (schema vazio) exportado com sucesso.")
            return True

        logger.info(f"  {table_name}: {total} registros (batch={batch_size}, heavy={is_heavy})")

        writer = None
        schema = None
        total_rows = 0

        cursor_name = f"etl_{table_name}_{uuid.uuid4().hex[:8]}"
        with conn.cursor(name=cursor_name) as cur:
            cur.itersize = batch_size
            cur.execute(select_sql)

            while True:
                rows = cur.fetchmany(batch_size)
                if not rows:
                    break

                pydict_rows = rows_to_pydict_list(columns, rows)
                arrow_table = pa.Table.from_pylist(pydict_rows)

                # Inicializa o writer com o schema do primeiro batch
                if writer is None:
                    fields = []
                    for field in arrow_table.schema:
                        if field.type == pa.null():
                            fields.append(pa.field(field.name, pa.string()))
                        else:
                            fields.append(field)
                    schema = pa.schema(fields)
                    writer = pq.ParquetWriter(temp_file, schema, compression="snappy")

                try:
                    cast_table = arrow_table.cast(schema, safe=False)
                    writer.write_table(cast_table)
                except Exception:
                    writer.write_table(arrow_table)

                total_rows += len(rows)
                if total_rows % 10000 < batch_size or total_rows <= batch_size:
                    logger.info(f"    {table_name}: {total_rows}/{total} linhas processadas...")

                del rows, pydict_rows, arrow_table
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
    
    cols = [
        "trace_id", "experiment_id", "experiment_name", "service_name",
        "data_hora_atendimento", "latencia_segundos", "status",
        "prompt_tokens", "completion_tokens", "total_tokens",
        "custo_usd", "custo_brl"
    ]
    temp_file = "/tmp/traces_consolidated.parquet"
    if os.path.exists(temp_file):
        os.remove(temp_file)

    query = f"""
    SELECT 
        t.request_id AS trace_id,
        t.experiment_id,
        COALESCE(e.name, 'Sem Experimento') AS experiment_name,
        COALESCE(tag_service."value", e.name, 'Agente Desconhecido') AS service_name,
        TO_TIMESTAMP(t.timestamp_ms / 1000.0) AS data_hora_atendimento,
        (t.execution_time_ms / 1000.0) AS latencia_segundos,
        t.status,
        
        -- Contagem de Tokens
        COALESCE(CAST(NULLIF(meta_prompt."value", '') AS INTEGER), 0) AS prompt_tokens,
        COALESCE(CAST(NULLIF(meta_comp."value", '') AS INTEGER), 0) AS completion_tokens,
        COALESCE(CAST(NULLIF(meta_total."value", '') AS INTEGER), 0) AS total_tokens,
        
        -- Custos
        COALESCE(CAST(NULLIF(meta_cost."value", '') AS NUMERIC(10, 6)), 0.0) AS custo_usd,
        ROUND(COALESCE(CAST(NULLIF(meta_cost."value", '') AS NUMERIC(10, 6)), 0.0) * {cotacao_dolar}, 4) AS custo_brl

    FROM "trace_info" t
    LEFT JOIN "experiments" e 
        ON t.experiment_id = CAST(e.experiment_id AS VARCHAR)
    LEFT JOIN "trace_tags" tag_service 
        ON t.request_id = tag_service.request_id 
        AND tag_service."key" = 'service.name'
    LEFT JOIN "trace_request_metadata" meta_prompt 
        ON t.request_id = meta_prompt.request_id 
        AND meta_prompt."key" = 'mlflow.trace.prompt_tokens'
    LEFT JOIN "trace_request_metadata" meta_comp 
        ON t.request_id = meta_comp.request_id 
        AND meta_comp."key" = 'mlflow.trace.completion_tokens'
    LEFT JOIN "trace_request_metadata" meta_total 
        ON t.request_id = meta_total.request_id 
        AND meta_total."key" = 'mlflow.trace.total_tokens'
    LEFT JOIN "trace_request_metadata" meta_cost 
        ON t.request_id = meta_cost.request_id 
        AND meta_cost."key" = 'mlflow.trace.cost'
    ORDER BY t.timestamp_ms DESC;
    """

    try:
        with conn.cursor() as cur:
            cur.execute(query)
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()

        if rows:
            logger.info(f"  Consolidados {len(rows)} traces com sucesso.")
            pydict_rows = rows_to_pydict_list(columns, rows)
            arrow_table = pa.Table.from_pylist(pydict_rows)
            pq.write_table(arrow_table, temp_file, compression="snappy")
        else:
            logger.info("  0 traces encontrados. Gerando Parquet de traces com schema...")
            empty_data = {col: pa.array([], type=pa.string()) for col in cols}
            empty_table = pa.Table.from_pydict(empty_data)
            pq.write_table(empty_table, temp_file, compression="snappy")

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
    logger.info("ETL MLflow PostgreSQL -> GCS Parquet (com Traces, Spans e Assessments)")
    logger.info("=" * 70)

    conn = get_connection()
    conn.set_session(readonly=True, autocommit=True)

    try:
        tables = get_public_tables(conn)
        logger.info(f"Encontradas {len(tables)} tabelas no banco: {', '.join(tables)}")

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
