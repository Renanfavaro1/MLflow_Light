# Guia de Setup - MLflow Light

## 1. Instalando o SDK

Para usar as funções do MLflow nos seus códigos locais, aplicações ou notebooks (Jupyter/Colab):

### Python:
```bash
pip install git+https://github.com/Renanfavaro1/MLflow_Light.git#subdirectory=sdk
```

### Node.js:
```bash
npm install git+https://github.com/Renanfavaro1/MLflow_Light.git#subdirectory=sdk-node
```

---

## 2. Configurando as Variáveis de Ambiente

Para enviar métricas e traces para o servidor oficial da Light, configure a URI e o Token corporativo:

### Linux / macOS:
```bash
export MLFLOW_TRACKING_URI="https://mlflow-tracking-server-504082412074.us-central1.run.app"
export MLFLOW_TRACKING_TOKEN="28684e077978582afa70be269dbdac57544aae36fb051fa3dc049f2e1c7defd0"
```

### Windows (PowerShell):
```powershell
$env:MLFLOW_TRACKING_URI="https://mlflow-tracking-server-504082412074.us-central1.run.app"
$env:MLFLOW_TRACKING_TOKEN="28684e077978582afa70be269dbdac57544aae36fb051fa3dc049f2e1c7defd0"
```

### Docker / Arquivo `.env`:
```env
MLFLOW_TRACKING_URI=https://mlflow-tracking-server-504082412074.us-central1.run.app
MLFLOW_TRACKING_TOKEN=28684e077978582afa70be269dbdac57544aae36fb051fa3dc049f2e1c7defd0
```

> 💡 **Nota de Segurança**: No GCP Cloud Run, o token pode ser injetado automaticamente via Secret Manager referenciando o secret `mlflow-api-token`.
