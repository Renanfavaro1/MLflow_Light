# Habilitar as APIs necessárias do GCP
resource "google_project_service" "gcp_services" {
  for_each = toset([
    "run.googleapis.com",
    "sqladmin.googleapis.com",
    "secretmanager.googleapis.com",
    "vpcaccess.googleapis.com",
    "compute.googleapis.com",
    "iam.googleapis.com",
    "servicenetworking.googleapis.com", # Faltava essa API para o peering do banco!
  ])
  service            = each.key
  project            = var.project_id
  disable_on_destroy = false
}

module "networking" {
  source = "./modules/networking"
  region = var.region
  
  # Força o módulo de rede a esperar todas as APIs ligarem primeiro
  depends_on = [google_project_service.gcp_services]
}

# Lê a senha salva manualmente no Secret Manager (Traga o seu próprio segredo)
data "google_secret_manager_secret_version" "db_password" {
  secret  = "mlflow-db-password"
  version = "latest"
  project = var.project_id
}

module "cloud_storage" {
  source     = "./modules/cloud_storage"
  project_id = var.project_id
  region     = var.region
}

module "cloud_sql" {
  source      = "./modules/cloud_sql"
  region      = var.region
  tier        = var.database_tier
  network_id  = module.networking.network_id
  db_password = data.google_secret_manager_secret_version.db_password.secret_data

  # Força o banco de dados a esperar a conexão VPC Peering ser concluída
  depends_on  = [module.networking]
}

# Cria um Secret com a URL do PostgreSQL para evitar que a senha fique visível no Cloud Run
resource "google_secret_manager_secret" "db_uri" {
  secret_id = "mlflow-backend-store-uri"
  project   = var.project_id
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "db_uri_version" {
  secret      = google_secret_manager_secret.db_uri.id
  secret_data = "postgresql://mlflow_user:${data.google_secret_manager_secret_version.db_password.secret_data}@${module.cloud_sql.db_host}:5432/mlflow"
}

# Dá permissão para o Cloud Run ler esse secret
resource "google_secret_manager_secret_iam_member" "cloud_run_secret_access" {
  secret_id = google_secret_manager_secret.db_uri.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${var.project_number}-compute@developer.gserviceaccount.com"
}

module "cloud_run" {
  source             = "./modules/cloud_run"
  project_id         = var.project_id
  region             = var.region
  service_name       = var.service_name
  image              = var.mlflow_image
  vpc_connector_id   = module.networking.vpc_connector_id
  bucket_name        = module.cloud_storage.bucket_name
  db_uri_secret_name = google_secret_manager_secret.db_uri.secret_id

  depends_on = [
    google_secret_manager_secret_version.db_uri_version,
    google_project_service.gcp_services
  ]
}

# --- ETL JOB: MLFLOW -> DATABRICKS ---

# Habilitar API do Cloud Scheduler
resource "google_project_service" "scheduler_api" {
  service            = "cloudscheduler.googleapis.com"
  project            = var.project_id
  disable_on_destroy = false
}

# Conta de Serviço para o Job
resource "google_service_account" "etl_job_sa" {
  account_id   = "mlflow-etl-job-sa"
  display_name = "Service Account for MLflow ETL Job"
  project      = var.project_id
}

# Permissão para o Job ler o Secret do Banco de Dados
resource "google_secret_manager_secret_iam_member" "etl_job_secret_access" {
  secret_id = google_secret_manager_secret.db_uri.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.etl_job_sa.email}"
}

# Permissão para o Job escrever no bucket GCS
resource "google_storage_bucket_iam_member" "etl_job_bucket_access" {
  bucket = module.cloud_storage.stats_bucket_name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.etl_job_sa.email}"
}

# Cloud Run Job
resource "google_cloud_run_v2_job" "etl_job" {
  name     = "mlflow-to-gcs-etl"
  location = var.region
  project  = var.project_id

  template {
    template {
      service_account = google_service_account.etl_job_sa.email
      
      vpc_access {
        connector = module.networking.vpc_connector_id
        egress    = "ALL_TRAFFIC"
      }

      containers {
        image = var.etl_image

        env {
          name  = "GCS_BUCKET_NAME"
          value = module.cloud_storage.stats_bucket_name
        }

        env {
          name = "DATABASE_URL"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.db_uri.secret_id
              version = "latest"
            }
          }
        }
      }
    }
  }

  depends_on = [
    google_secret_manager_secret_version.db_uri_version,
    module.networking
  ]
}

# Conta de serviço para o Scheduler invocar o Cloud Run
resource "google_service_account" "scheduler_sa" {
  account_id   = "mlflow-scheduler-sa"
  display_name = "Service Account for Cloud Scheduler"
  project      = var.project_id
}

# Permissão para o Scheduler invocar Jobs
resource "google_project_iam_member" "scheduler_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.scheduler_sa.email}"
}

# Cloud Scheduler
resource "google_cloud_scheduler_job" "etl_trigger" {
  name        = "mlflow-etl-diario"
  description = "Dispara o Job de ETL do MLflow diariamente"
  schedule    = var.etl_schedule
  time_zone   = "America/Sao_Paulo"
  region      = var.region
  project     = var.project_id

  http_target {
    http_method = "POST"
    uri         = "https://${var.region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${var.project_id}/jobs/mlflow-to-gcs-etl:run"

    oauth_token {
      service_account_email = google_service_account.scheduler_sa.email
    }
  }

  depends_on = [
    google_cloud_run_v2_job.etl_job,
    google_project_service.scheduler_api
  ]
}

