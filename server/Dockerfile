FROM ghcr.io/mlflow/mlflow:latest

COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

# Copy and setup entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose MLflow port
EXPOSE 5000

# Set the entrypoint
ENTRYPOINT ["/entrypoint.sh"]
