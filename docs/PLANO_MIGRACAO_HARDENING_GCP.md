# 📋 Plano de Migração e Hardening de Infraestrutura (GCP)

> **Documento de Referência Técnica**: Este guia reúne todas as melhorias de segurança, performance, resiliência e boas práticas identificadas no Cloud SQL e Cloud Run para serem aplicadas durante a **migração do MLflow da Light para o novo projeto no GCP**.

---

## 🎯 1. Diagnóstico e Alertas Identificados no Cloud SQL

Na auditoria de saúde da instância atual (`mlflow-db-instance`), foram identificados 6 pontos de alta prioridade pelo Google Cloud Security Advisor:

| Item | Alerta GCP | Causa Raiz | Impacto |
|---|---|---|---|
| **1** | *No automated backup policy* | Falta do bloco `backup_configuration` no Terraform | Risco de perda permanente de dados em caso de corrupção ou exclusão acidental. |
| **2** | *High resource utilization* | Instância `db-f1-micro` (0.6 GB RAM) | Sobrecarga com 98k+ traces e múltiplos workers do Cloud Run. |
| **3** | *Connections impacting performance* | Pool de conexões saturando máquina micro | Latência e quedas intermitentes sob concorrência. |
| **4** | *Allows unencrypted direct connections* | `ssl_mode` não restrito a `ENCRYPTED_ONLY` | Conexões sem exigência explícita de TLS/SSL. |
| **5** | *Connection attempts not logged* | Flag `log_connections` desativada | Ausência de trilha de auditoria para tentativas de conexão. |
| **6** | *Disconnections not logged* | Flag `log_disconnections` desativada | Falta de visibilidade sobre encerramento anômalo de sessões. |

---

## 🛡️ 2. Código Terraform Atualizado (Para o Novo Projeto)

### A. Módulo Cloud SQL (`infrastructure/modules/cloud_sql/main.tf`)

Substitua o conteúdo do módulo pelo código abaixo:

```hcl
variable "region" {}
variable "tier" {}
variable "network_id" {}
variable "db_password" {}

resource "google_sql_database_instance" "mlflow_db_instance" {
  name             = "mlflow-db-instance"
  database_version = "POSTGRES_15"
  region           = var.region

  settings {
    # Máquina com 2 vCPUs e 7.5GB RAM para alta concorrência de Traces
    tier = var.tier

    # 1. Segurança de Rede e Criptografia em Trânsito
    ip_configuration {
      ipv4_enabled    = false            # Desativa IP público (Segurança)
      private_network = var.network_id   # Acesso exclusivo via VPC Peering
      ssl_mode        = "ENCRYPTED_ONLY" # Força criptografia TLS/SSL
    }

    # 2. Política de Backup Automático e Recuperação Point-in-Time (PITR)
    backup_configuration {
      enabled                        = true
      start_time                     = "02:00" # 23:00 (Horário de Brasília)
      point_in_time_recovery_enabled = true   # Restauração a qualquer minuto nos últimos 7 dias
      transaction_log_retention_days = 7
      backup_retention_settings {
        retained_backups = 7
        retention_unit   = "COUNT"
      }
    }

    # 3. Auditoria e Logs de Performance
    database_flags {
      name  = "log_connections"
      value = "on"
    }
    database_flags {
      name  = "log_disconnections"
      value = "on"
    }
    database_flags {
      name  = "log_min_duration_statement"
      value = "2000" # Registra queries que demorarem mais de 2s
    }
  }

  # Impede exclusão acidental do banco
  deletion_protection = true
}

resource "google_sql_database" "mlflow_db" {
  name     = "mlflow"
  instance = google_sql_database_instance.mlflow_db_instance.name
}

resource "google_sql_user" "mlflow_user" {
  name     = "mlflow_user"
  instance = google_sql_database_instance.mlflow_db_instance.name
  password = var.db_password
}

output "connection_name" {
  value = google_sql_database_instance.mlflow_db_instance.connection_name
}

output "db_host" {
  value = google_sql_database_instance.mlflow_db_instance.private_ip_address
}
```

### B. Variáveis do Terraform (`infrastructure/variables.tf`)

Atualize o tier padrão do banco:

```hcl
variable "database_tier" {
  description = "Cloud SQL machine tier"
  type        = string
  # db-custom-2-7680 (2 vCPU, 7.5GB RAM) para suportar 100k+ traces com folga
  default     = "db-custom-2-7680"
}
```

---

## 🚚 3. Roteiro de Migração de Dados (Passo a Passo)

Quando o novo projeto no GCP for ativado, siga este procedimento para migrar os 100k+ registros históricos sem perda de dados:

### Passo 1: Exportar Dump do Banco Atual
No Cloud SQL atual, gere um dump via Cloud Storage ou terminal:

```bash
# Via gcloud (direto para o bucket de transição)
gcloud sql export sql mlflow-db-instance gs://SEU_BUCKET_TRANSICAO/mlflow_dump_backup.sql \
  --database=mlflow \
  --project=light-energia-dev-a39122fa
```

### Passo 2: Provisionar a Nova Infraestrutura via Terraform
No novo projeto GCP:

```bash
cd infrastructure
terraform init
terraform plan -var="project_id=NOVO_PROJECT_ID" -var="project_number=NOVO_PROJECT_NUMBER"
terraform apply -auto-approve
```

### Passo 3: Importar o Dump no Novo Cloud SQL
No novo projeto:

```bash
gcloud sql import sql mlflow-db-instance gs://SEU_BUCKET_TRANSICAO/mlflow_dump_backup.sql \
  --database=mlflow \
  --project=NOVO_PROJECT_ID
```

### Passo 4: Migrar Artefatos do Cloud Storage
Copiar os artefatos de modelos e exports históricos entre buckets:

```bash
gcloud storage rsync -r gs://mlflow-artifacts-light-energia-dev-a39122fa gs://mlflow-artifacts-NOVO_PROJECT_ID
```

---

## 🔑 4. Checklist de Secrets no Novo Projeto

Certifique-se de que os seguintes secrets estejam criados no Secret Manager do novo projeto:

1. `mlflow-db-password`: Senha do usuário `mlflow_user`.
2. `mlflow-api-token`: Token corporativo compartilhado com os Agentes de IA (`28684e077978582afa...`).
3. `mlflow-backend-store-uri`: Gerado automaticamente pelo Terraform apontando para o IP privado do novo Cloud SQL.

---

## 📈 5. Dimensionamento Recomendado por Ambiente

| Componente | Ambiente DEV | Ambiente PROD |
|---|---|---|
| **Cloud SQL Tier** | `db-custom-2-7680` (2 vCPU, 7.5 GB) | `db-custom-4-15360` (4 vCPU, 15 GB) |
| **Cloud SQL Availability** | ZONAL | REGIONAL (Alta Disponibilidade com Failover) |
| **Cloud Run Memory** | 4 GiB (2 workers) | 8 GiB (4 workers) |
| **Cloud Run Max Instances** | 10 | 100 |
| **Backup Retention** | 7 dias | 30 dias (com Point-in-Time Recovery) |
