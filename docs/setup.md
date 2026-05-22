# Guia de Setup - MLflow Light

## 1. Instalando o SDK
Para que os cientistas de dados possam usar as funções do MLflow nos seus códigos locais ou nos notebooks (Jupyter/Colab):
```bash
pip install git+https://github.com/Renanfavaro1/MLflow_Light.git#subdirectory=sdk
```

## 2. Configurando o Ambiente
Como o servidor MLflow estará rodando no Cloud Run de forma privada, será necessário definir a variável de ambiente apontando para ele:
```bash
export MLFLOW_TRACKING_URI="https://<SUA-URL-DO-CLOUD-RUN>"
```
Se estiver rodando na máquina local sem conexão direta (ou sem IAP token), os códigos salvarão os experimentos na pasta `./mlruns` automaticamente.
