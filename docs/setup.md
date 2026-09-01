# Guia de Setup & Acesso - MLflow Light

---

## 🌐 1. Acesso à Área Light (Interface Visual)

Para acessar o painel de experimentos, métricas e traces no navegador:

- **URL**: `https://mlflow-tracking-server-504082412074.us-central1.run.app`
- **Usuário**: `light`
- **Senha**: `Light@2026`

---

## 📦 2. Instalando os SDKs da Light

### Python:
```bash
pip install git+https://github.com/Renanfavaro1/MLflow_Light.git#subdirectory=sdk
```

### Node.js / TypeScript:
```bash
npm install git+https://github.com/Renanfavaro1/MLflow_Light.git#subdirectory=sdk-node
```

---

## ⚙️ 3. Configurando as Variáveis de Ambiente

Para conectar suas aplicações ao servidor oficial:

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

### Arquivo `.env` ou Docker Compose:
```env
MLFLOW_TRACKING_URI=https://mlflow-tracking-server-504082412074.us-central1.run.app
MLFLOW_TRACKING_TOKEN=28684e077978582afa70be269dbdac57544aae36fb051fa3dc049f2e1c7defd0
```

---

## 🚀 4. Build e Deploy do Servidor (Infraestrutura)

Caso necessite atualizar a imagem ou re-implantar a infraestrutura no GCP:

```bash
# 1. No Cloud Shell, clone ou atualize o repositório
cd ~/MLflow_Light
git pull origin main

# 2. Build da imagem com o plugin light-auth
gcloud builds submit ./server --tag us-central1-docker.pkg.dev/light-energia-dev-a39122fa/mlflow-repo/mlflow:latest

# 3. Deploy no Cloud Run
gcloud run deploy mlflow-tracking-server \
  --image us-central1-docker.pkg.dev/light-energia-dev-a39122fa/mlflow-repo/mlflow:latest \
  --region us-central1
```
