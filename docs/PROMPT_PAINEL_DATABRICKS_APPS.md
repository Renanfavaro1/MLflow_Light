# PROMPT MESTRE: Painel de Auditoria e Observabilidade de IA (Databricks Apps)

> **Instruções:** Copie todo o conteúdo deste arquivo e cole no prompt inicial da nova aba do Antigravity para iniciar o desenvolvimento do projeto **Painel MLflow**.

---

```markdown
# Contexto do Projeto: Painel de Observabilidade, Auditoria e Qualidade de IA (MLflow Light)

Você é o Arquiteto de Software e Engenheiro Full-Stack sênior encarregado de criar o **Painel de Observabilidade, Auditoria e Governança de IA da Light**.
A aplicação será hospedada no **Databricks Apps** e consumirá diretamente as tabelas do **Unity Catalog** geradas pelo pipeline de observabilidade do MLflow no catálogo `mlflow_light_dev`.

---

## 🎯 1. Objetivo da Aplicação
Construir uma aplicação Full-Stack completa (Backend em **Python FastAPI** + Frontend em **React Vite** com visual moderno e responsivo) que atenda três perfis principais da Light:

1. **Área de Negócio e Diretoria (Visão Executiva):**
   - Volume consolidado de atendimentos por ferramenta de IA (Chatbot Código de Ética, Veritas, Normas Técnicas, etc.) e por ambiente (DEV, HML, PROD).
   - Taxa de sucesso/resolução e tempo médio de resposta (latência).
   - Gestão financeira consolidada: custo total (USD e BRL) e consumo de tokens por dia/mês.

2. **Área de Auditoria, Risco e Compliance (Visão Micro / Interações):**
   - Tela de auditoria estilo conversa/chat para inspecionar casos específicos.
   - Visualização do que o usuário enviou, fontes consultadas no RAG, ferramentas acionadas pela IA e a resposta final gerada.
   - Visualização de notas de avaliação de qualidade (LLM as a Judge) e feedbacks registrados.

3. **Engenharia de IA e MLOps (Visão Técnica):**
   - Distribuição de chamadas por modelo (Gemini 3.7 Flash, 3.5 Flash, Flash-Lite, etc.).
   - Erros operacionais, stack traces e latência detalhada por span de execução.

---

## 🗄️ 2. Catálogo e Tabelas do Unity Catalog (Databricks)
O catálogo já provisionado no Databricks é **`mlflow_light_dev`**. As principais tabelas disponíveis são:

* **`mlflow_light_dev.runs`**: Registra cada execução/chamada (`run_uuid`, `experiment_id`, `status`, `start_time`, `end_time`).
* **`mlflow_light_dev.experiments`**: Mapeia o nome dos projetos (`name`, `experiment_id`, `artifact_location`).
* **`mlflow_light_dev.tags`**: Metadados de negócio associados à run (`run_uuid`, `key`, `value` — ex: `area_negocio`, `canal`, `session_id`, `user_id`, `ambiente`).
* **`mlflow_light_dev.latest_metrics`**: Métricas de consumo e performance (`run_uuid`, `key`, `value` — ex: `llm.usage.total_tokens`, `llm.cost.total_cost`, `llm.latency_seconds`).
* **`mlflow_light_dev.span_metrics`**: Métricas granulares de chamadas internas de ferramentas e LLMs.
* **`mlflow_light_dev.inputs`** e **`input_tags`**: Entradas e conjuntos de dados manipulados.

---

## 🔐 3. Autenticação e Permissionamento (Databricks Apps)
A aplicação roda sob a infraestrutura gerenciada do **Databricks Apps**:
* **SSO e Identidade:** O proxy reverso do Databricks injeta automaticamente o cabeçalho HTTP `X-Forwarded-Email` ou `X-Forwarded-User` em cada requisição. O backend deve ler esse cabeçalho para saber quem está acessando.
* **Conexão com o Banco:** Utilizar o conector oficial `databricks-sql-connector` e `databricks-sdk` com a autenticação padrão do ambiente do Databricks Apps (Service Principal ou OAuth do Workspace), sem hardcode de credenciais ou senhas.
* **Perfis de Acesso (RBAC):**
  - **Auditoria/Compliance:** Acesso à listagem de mensagens, textos de conversas e notas de qualidade.
  - **Negócio/Gestão:** Acesso aos cards de KPIs, gráficos de custos consolidados e tendências.
  - **Admin/Engenharia:** Acesso completo, visualização de logs brutos e spans técnicos.

---

## 🛠️ 4. Stack Tecnológica e Arquitetura

### Backend: Python 3.11+ / FastAPI
* Servidor REST rápido com documentação automática Swagger (`/docs`).
* Endpoints otimizados com consultas agregadas via SQL no Databricks SQL Warehouse:
  - `GET /api/me`: Retorna o usuário logado (via headers do Databricks) e seu perfil de permissão.
  - `GET /api/experiments`: Lista todas as ferramentas/experimentos cadastrados.
  - `GET /api/kpis`: Métricas agregadas (total de conversas, latência média, custo total, taxa de sucesso) com filtros de data e projeto.
  - `GET /api/costs`: Série temporal de tokens e custos desagregados por modelo de IA.
  - `GET /api/interactions`: Lista paginada das execuções com busca textual e filtros.
  - `GET /api/interactions/{run_id}`: Detalhes de uma conversa (pergunta, resposta, fontes RAG, tokens consumidos).
* Serve os arquivos compilados do frontend React (`frontend/dist`) em uma porta única configurada pelo Databricks Apps (porta lida de `DATABRICKS_APP_PORT` ou 8000).

### Frontend: React 18/19 + Vite
* **Design & Estilo:** Interface moderna, responsiva, com suporte a Dark/Light Mode, tipografia profissional (Inter), cartões com efeito clean/glassmorphism e paleta harmoniosa.
* **Gráficos:** Recharts ou Chart.js para consumo de tokens por dia, evolução de custos e distribuição de modelos.
* **Componentes Principais:**
  - **Barra Superior (Header):** Identificação do usuário logado na Light, seletor de projeto/ambiente e alternador de tema.
  - **Filtros Globais:** Período (Últimos 7 dias, 15 dias, 30 dias, Custom), Ambiente (DEV / HML / PROD) e Ferramenta.
  - **Grid de KPIs:** Cards com Total de Atendimentos, Custo Estimado (USD/BRL), Latência Média e Assertividade.
  - **Tabela de Interações:** Tabela com busca rápida, status (Sucesso/Falha), timestamp, modelo utilizado e botão para abrir detalhes.
  - **Modal de Auditoria (Visualizador de Chat):** Exibe a interação no formato de mensagem de chat, com aba lateral mostrando as fontes documentais consultadas (RAG) e os metadados da execução.

### Manifesto Databricks Apps (`app.yaml`):
* Definir o comando de inicialização com Uvicorn e os pacotes necessários no `requirements.txt`.

---

## 📂 5. Estrutura de Pastas do Projeto
```text
painel-mlflow/
├── app.yaml                 # Manifesto oficial do Databricks Apps
├── requirements.txt         # Dependências do backend Python
├── server/
│   ├── main.py              # Aplicação FastAPI e rotas de API
│   ├── config.py            # Leitura de variáveis do Databricks Apps
│   ├── db.py                # Conexão com Databricks SQL Warehouse
│   └── queries.py           # Queries SQL otimizadas no catálogo mlflow_light_dev
└── frontend/
    ├── package.json
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── App.jsx
        ├── main.jsx
        ├── index.css
        ├── components/
        │   ├── Header.jsx
        │   ├── KpiCards.jsx
        │   ├── CostChart.jsx
        │   ├── InteractionsTable.jsx
        │   └── InteractionModal.jsx
        └── services/
            └── api.js
```

---

## 🚀 O que fazer primeiro:
1. Apresentar o plano detalhado de componentes e endpoints.
2. Criar o arquivo `app.yaml` e as dependências em `requirements.txt`.
3. Implementar a camada de conexão com o banco (`server/db.py` e `server/queries.py`) consumindo o catálogo `mlflow_light_dev`.
4. Construir o servidor FastAPI (`server/main.py`) com tratamento dos headers de SSO do Databricks.
5. Construir o frontend React completo com os componentes visuais de KPIs, gráficos e auditoria de conversas.
```
