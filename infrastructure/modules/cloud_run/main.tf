variable "project_id" {}
variable "region" {}
variable "service_name" {}
variable "image" {}
variable "vpc_connector_id" {}
variable "bucket_name" {}
variable "db_uri_secret_name" {}

resource "google_cloud_run_v2_service" "mlflow_server" {
  name     = var.service_name
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL" # Permite acesso da internet (da sua máquina local)

  template {
    scaling {
      max_instance_count = 100
    }
    max_instance_request_concurrency = 80

    containers {
      image = var.image

      # Artefatos vão para o GCS
      env {
        name  = "DEFAULT_ARTIFACT_ROOT"
        value = "gs://${var.bucket_name}"
      }

      # A URL de conexão do banco vem de um Secret do Secret Manager (muito mais seguro)
      env {
        name = "BACKEND_STORE_URI"
        value_source {
          secret_key_ref {
            secret  = var.db_uri_secret_name
            version = "latest"
          }
        }
      }

      # Evita o erro "Invalid Host header - possible DNS rebinding attack" no MLflow 2.15+
      env {
        name  = "MLFLOW_SERVER_ALLOWED_HOSTS"
        value = "*"
      }

      # Permite que a interface web faça requisições AJAX para a própria API do MLflow
      env {
        name  = "MLFLOW_SERVER_CORS_ALLOWED_ORIGINS"
        value = "*"
      }

      ports {
        container_port = 5000
      }
      
      resources {
        limits = {
          cpu    = "2"
          memory = "2Gi"
        }
      }
    }

    # Conecta o Cloud Run na VPC para conseguir enxergar o IP privado do Cloud SQL
    vpc_access {
      connector = var.vpc_connector_id
      egress    = "ALL_TRAFFIC"
    }
  }

  lifecycle {
    ignore_changes = [
      template[0].containers[0].image, # Ignora mudanças de imagem (serão feitas via CI/CD)
    ]
  }
}

output "service_url" {
  value = google_cloud_run_v2_service.mlflow_server.uri
}

# Permite acesso público para testes e uso da interface web sem tokens complexos
resource "google_cloud_run_v2_service_iam_member" "public_access" {
  project  = google_cloud_run_v2_service.mlflow_server.project
  location = google_cloud_run_v2_service.mlflow_server.location
  name     = google_cloud_run_v2_service.mlflow_server.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
