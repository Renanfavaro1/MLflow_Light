output "mlflow_url" {
  description = "URL do servidor MLflow no Cloud Run"
  value       = module.cloud_run.service_url
}

output "database_connection_name" {
  description = "Nome da conexão do banco de dados Cloud SQL"
  value       = module.cloud_sql.connection_name
}

output "artifact_bucket_name" {
  description = "Nome do bucket GCS para os artefatos do MLflow"
  value       = module.cloud_storage.bucket_name
}
