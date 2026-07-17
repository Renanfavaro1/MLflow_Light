variable "project_id" {}
variable "region" {}

resource "google_storage_bucket" "mlflow_artifacts" {
  # O nome do bucket precisa ser globalmente único
  name          = "mlflow-artifacts-${var.project_id}"
  location      = var.region
  force_destroy = true # Permite deletar o bucket pelo Terraform mesmo se tiver arquivos

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }
}

output "bucket_name" {
  value = google_storage_bucket.mlflow_artifacts.name
}

resource "google_storage_bucket" "mlflow_stats" {
  name          = "mlflow-stats-${var.project_id}"
  location      = var.region
  force_destroy = true

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }
}

output "stats_bucket_name" {
  value = google_storage_bucket.mlflow_stats.name
}
