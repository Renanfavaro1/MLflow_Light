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
- `sdk-node/`: Pacote Node.js (TypeScript/JS) contendo wrappers e funções para integração com aplicações web e backends JS.
- `examples/`: Exemplos práticos de uso do SDK e tracking de experimentos.
- `docs/`: Documentação detalhada sobre arquitetura, setup e guias de uso.

## Autenticação
O acesso ao Tracking Server do MLflow é livre para a rede interna da Light. **Nenhuma autenticação (como IAP, Firebase ou Basic Auth) é exigida para os Cientistas de Dados** ou aplicações que logam as métricas via SDK. Toda a responsabilidade de acesso seguro aos recursos do GCP (Cloud SQL e Storage) fica a cargo exclusivo do MLflow Server via IAM (Service Accounts).

## Requisitos para os Usuários (Projetos e Assistentes)
- Python 3.9+ ou Node.js (se usar o SDK JS)
- Git (para baixar o pacote)
