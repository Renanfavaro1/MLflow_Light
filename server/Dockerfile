FROM ghcr.io/mlflow/mlflow:latest

# Install dependencies required for GCP integration and PostgreSQL
RUN pip install --no-cache-dir \
    psycopg2-binary \
    google-cloud-storage \
    gunicorn

# Copy and setup entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose MLflow port
EXPOSE 5000

# Set the entrypoint
ENTRYPOINT ["/entrypoint.sh"]
