terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }
  }

  # Configuração do backend remoto (Cloud Storage) para salvar o state do Terraform
  # Descomente e ajuste o nome do bucket após criá-lo manualmente ou via script separado
  # backend "gcs" {
  #   bucket = "light-tf-state-bucket"
  #   prefix = "terraform/mlflow/state"
  # }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}
