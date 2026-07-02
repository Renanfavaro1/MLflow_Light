# Guia de Setup - MLflow Light

## 1. Instalando o SDK
Para que os cientistas de dados possam usar as funções do MLflow nos seus códigos locais ou nos notebooks (Jupyter/Colab):
```bash
pip install git+https://github.com/Renanfavaro1/MLflow_Light.git#subdirectory=sdk
```

## 2. Configurando o Ambiente
Como o servidor MLflow está rodando na nuvem, você deve apontar o seu código para a URL oficial da Light:

**Linux/Mac:**
```bash
export MLFLOW_TRACKING_URI="https://mlflow-tracking-server-504082412074.us-central1.run.app"
```

**Windows (PowerShell):**
```powershell
$env:MLFLOW_TRACKING_URI="https://mlflow-tracking-server-504082412074.us-central1.run.app"
```

Se estiver rodando o código sem essa variável configurada, os rastreamentos salvarão os arquivos na sua máquina local de forma indesejada.
