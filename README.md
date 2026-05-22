# MLflow na Light — Remote Tracking Server no GCP

> **Repositório**: [https://github.com/Renanfavaro1/MLflow_Light.git](https://github.com/Renanfavaro1/MLflow_Light.git)

Implementação completa do MLflow na Light utilizando a arquitetura **Remote Tracking with Server**, hospedado inteiramente no Google Cloud Platform. 

O sistema atende a dois cenários principais da Light:
1. **Modelos de ML tradicionais** — treinamento, avaliação, versionamento de modelos (sklearn, XGBoost, etc.)
2. **Softwares com Foundation Models via API** — tracking de chamadas a LLMs (Gemini, OpenAI, etc.), prompts, tokens, latência e custos, incluindo frameworks de avaliação como LLM as a Judge e Spans para pipelines complexos (RAG, Agentes).

## Estrutura do Repositório

- `infrastructure/`: Configurações do Terraform para provisionar Cloud SQL, Cloud Storage, Cloud Run, VPC, IAM, etc.
- `server/`: Container Docker customizado para rodar o MLflow Tracking Server conectado aos serviços GCP.
- `sdk/`: Pacote Python `light-mlflow` contendo decorators simplificados e integrações específicas para os times da Light.
- `examples/`: Exemplos práticos de uso do SDK e tracking de experimentos.
- `docs/`: Documentação detalhada sobre arquitetura, setup e guias de uso.

## Autenticação
A interface web do MLflow será protegida usando Firebase Authentication (mesmo projeto do Veritas), permitindo acesso seguro via e-mail e senha.

## Requisitos
- Conta GCP com permissões no projeto `light-energia-dev-a39122fa`
- Terraform >= 1.5
- Docker
- Python 3.9+
