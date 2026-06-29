variable "region" {}
variable "tier" {}
variable "network_id" {}
variable "db_password" {}

resource "google_sql_database_instance" "mlflow_db_instance" {
  name             = "mlflow-db-instance"
  database_version = "POSTGRES_15"
  region           = var.region

  settings {
    # Para suportar milhares de conexões simultâneas do Assistente Virtual, 
    # recomenda-se o uso de um tier como 'db-custom-2-7680' ou superior no ambiente de Produção.
    tier = var.tier
    ip_configuration {
      ipv4_enabled    = false # Desativa IP público (Segurança)
      private_network = var.network_id
    }
  }

  # Impede exclusão acidental do banco de dados
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
