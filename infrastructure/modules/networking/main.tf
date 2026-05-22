variable "region" {}

resource "google_compute_network" "mlflow_vpc" {
  name                    = "mlflow-vpc"
  auto_create_subnetworks = true
}

# Reserva um range de IP para o banco de dados interno
resource "google_compute_global_address" "private_ip_address" {
  name          = "mlflow-db-private-ip"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.mlflow_vpc.id
}

# Cria a conexão da VPC com os serviços do Google (permite o Cloud SQL privado)
resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.mlflow_vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_address.name]
}

# Conector Serverless para o Cloud Run acessar a VPC
resource "google_vpc_access_connector" "connector" {
  name          = "mlflow-vpc-conn"
  region        = var.region
  network       = google_compute_network.mlflow_vpc.name
  ip_cidr_range = "10.8.0.0/28"
}

output "network_id" {
  value = google_compute_network.mlflow_vpc.id
}

output "vpc_connector_id" {
  value = google_vpc_access_connector.connector.id
}
