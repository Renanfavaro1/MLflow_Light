variable "project_id" {
  description = "GCP Project ID"
  type        = string
  default     = "light-energia-dev-a39122fa"
}

variable "project_number" {
  description = "GCP Project Number"
  type        = string
  default     = "504082412074"
}

variable "region" {
  description = "GCP Region for all resources"
  type        = string
  default     = "us-central1"
}

variable "database_tier" {
  description = "Cloud SQL machine tier"
  type        = string
  default     = "db-f1-micro"
}

variable "mlflow_image" {
  description = "Docker image for the MLflow server"
  type        = string
  # Esta variável deverá ser preenchida com o Artifact Registry path da imagem após o build
  default     = "us-central1-docker.pkg.dev/light-energia-dev-a39122fa/mlflow-repo/mlflow:latest"
}

variable "service_name" {
  description = "Name for the Cloud Run service"
  type        = string
  default     = "mlflow-tracking-server"
}
