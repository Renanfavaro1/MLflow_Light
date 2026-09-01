FROM ghcr.io/mlflow/mlflow:latest

COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

# Copia e instala o plugin de autenticação do MLflow
COPY setup.py /app/setup.py
COPY light_auth /app/light_auth
RUN pip install --no-cache-dir -e /app

# Entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 5000

ENTRYPOINT ["/entrypoint.sh"]
