# SDK Light MLflow (Python)

Pacote oficial da Light para observabilidade de Inteligência Artificial Generativa (LLMs, RAGs e Agentes) e tracking de modelos de Machine Learning (Scikit-Learn, XGBoost, PyTorch).

## 🚀 Instalação

```bash
pip install git+https://github.com/Renanfavaro1/MLflow_Light.git#subdirectory=sdk
```

## ⚙️ Configuração Básica

```python
from light_mlflow import LightMLflowConfig
from light_mlflow.decorators import track_pipeline, llm_span, tool_span

# Inicializa lendo MLFLOW_TRACKING_URI e MLFLOW_TRACKING_TOKEN do ambiente
LightMLflowConfig.setup(experiment_name="Meu_Projeto_IA")
```

## 🛡️ Destaques
- **Fail-Safe Nativo**: O rastreamento nunca derruba sua aplicação se o MLflow estiver fora do ar ou sem credencial.
- **Árvore de Traces Automática**: Integração direta com OpenAI, Google Gemini, Anthropic Claude.
- **Cálculo Automático de Custos e Tokens**: Precificação atualizada dos principais modelos do mercado.
