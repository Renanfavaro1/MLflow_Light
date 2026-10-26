# Arquitetura Corporativa: MLflow 3 AI Gateway & Hub de Observabilidade GenAI (Light)

---

## 📋 Sumário Executivo
Este documento consolida a arquitetura de referência, as decisões técnicas, os padrões de segurança e o plano de implantação do **MLflow 3 AI Gateway** como a plataforma centralizada de **Governança, Observabilidade e Roteamento de Inteligência Artificial da Light**.

O sistema atua como o ponto único de entrada para todas as inferências de Foundation Models (Google Gemini, Anthropic Claude via Vertex AI) consumidas tanto por **Agentes de Código (Claude Code, Antigravity, Cursor)** quanto por **Aplicações de Negócio (Chatbots de Atendimento, RAGs, Veritas, AGV)**, garantindo controle orçamentário rígido, conformidade com a LGPD e integração total com o ecossistema corporativo da Light (SSO NAM, Shared VPC e Cloud Run).

---

## 🏛️ 1. Visão Geral da Arquitetura & O Novo MLflow 3.15+

A versão **MLflow 3.15+** transforma o MLflow de um simples rastreador de modelos clássicos em um **Hub de Engenharia de GenAI**:

```
                                  USUÁRIOS & FERRAMENTAS DA LIGHT
          ┌──────────────────────────────────────┼──────────────────────────────────────┐
          │                                      │                                      │
          ▼                                      ▼                                      ▼
┌──────────────────┐                   ┌──────────────────┐                   ┌──────────────────┐
│  Coding Agents   │                   │ Chatbots & RAGs  │                   │ Gestão & FinOps  │
│ Claude Code, CLI │                   │ AGV, Veritas, BT │                   │ Visualizadores   │
│ Antigravity, IDE │                   │ (Cloud Run / SDK)│                   │ Web UI (Browser) │
└─────────┬────────┘                   └─────────┬────────┘                   └─────────┬────────┘
          │                                      │                                      │
          │ Bearer Token Google/NAM              │ Service Account IAM                  │ SSO NAM (Browser)
          ▼                                      ▼                                      ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────┐
│                       MLFLOW TRACKING SERVER & AI GATEWAY (Cloud Run)                          │
│                                                                                                │
│ ┌──────────────────────┐ ┌──────────────────────┐ ┌───────────────────┐ ┌────────────────────┐ │
│ │  light-auth Plugin   │ │  Budgets & Limits    │ │ Usage & Tracing   │ │ MCP Registry       │ │
│ │  Validação Token/NAM │ │  (Teto USD/Bloqueio) │ │ Métricas de Tokens│ │ Ferramentas Agente │ │
│ └──────────────────────┘ └──────────────────────┘ └───────────────────┘ └────────────────────┘ │
│ ────────────────────────────────────────────────────────────────────────────────────────────── │
│ ┌────────────────────────────────────────────────────────────────────────────────────────────┐ │
│ │                            AI GATEWAY ENDPOINTS (Model Router)                             │ │
│ │  • chat-fast (Gemini 2.5 Flash)      • code-expert (Claude 3.5 Sonnet)                     │ │
│ │  • deep-context (Gemini 1.5 Pro)     • fallback-chain (Failover Automático)                │ │
│ └────────────────────────────────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────┬───────────────────────────────┬────────────────────────────────┘
                                │                               │
                     VPC Egress │ Interno                       │ Cloud SQL Peering (PSA)
                                ▼                               ▼
                ┌───────────────────────────────┐ ┌───────────────────────────────┐
                │ Google Vertex AI Model Garden │ │ Cloud SQL (PostgreSQL 15)     │
                │ • Google Gemini (Flash / Pro) │ │ Metadados, Runs, Spans,       │
                │ • Anthropic Claude (Sonnet/HK)│ │ Traces e Logs de Usuários     │
                └───────────────────────────────┘ └───────────────────────────────┘
```

### Novos Módulos do MLflow 3.15 em Destaque:
1. **AI Gateway (New)**: Proxy reverso seguro que centraliza conexões com provedores de IA, gerencia credenciais de forma criptografada e aplica governança de custos.
2. **Usage & Budgets**:
   - *Usage*: Painel analítico em tempo real de contagem de tokens (prompt, completion) e custos financeiros em USD.
   - *Budgets*: Mecanismo ativo de defesa que dispara alertas ou bloqueia chamadas com `HTTP 429` ao atingir limites diários ou mensais, eliminando o risco de *Denial of Wallet* (OWASP LLM04).
3. **MCP Registry (Beta)**: Catálogo corporativo para o *Model Context Protocol*, permitindo que agentes descubram servidores de ferramentas internos da Light (APIs do SAP, bancos de dados, normas técnicas) de forma auditada.
4. **Prompts & Playground**: Ambiente web para versionamento, teste e homologação de prompts com suporte a aliases (`@staging`, `@production`).

---

## 🔄 2. Relação entre AI Gateway e o SDK `light-mlflow`

O AI Gateway e os decoradores do SDK corporativo **não são concorrentes; são camadas complementares**:

| Camada | Ferramenta | O que rastreia / executa |
| :--- | :--- | :--- |
| **Camada de Infraestrutura & LLM** | **MLflow AI Gateway** | Tráfego HTTP do modelo, tokens gastos, tempo de inferência, custo em USD e bloqueio por budget. |
| **Camada de Negócio & Aplicação** | **SDK `light-mlflow`** | Orquestração do agente (`@track_pipeline`), chamadas a sistemas legados (`@tool_span`), busca vetorial/RAG (`@retriever_span`) e lógica interna (`@agent_span`). |

### Estrutura Hierárquica do Trace Gerado:
```text
Pipeline_Atendimento_Cliente (@track_pipeline)
  ├── Consultar_Debitos_SAP (@tool_span) ➔ [Tempo: 180ms, Status: OK]
  ├── Buscar_Norma_Regulatoria (@retriever_span) ➔ [Tempo: 95ms, 3 docs retornados]
  └── Inferencia_Vertex_Gateway (@llm_span) ➔ [Passa pelo AI Gateway: registra tokens e valida budget]
```

---

## ☁️ 3. Google Vertex AI como Provedor Único de Modelos

A Light padroniza o **Google Vertex AI** como o provedor central do Gateway.

### Vantagens Estratégicas:
1. **Multi-Modelos sem Contratos Adicionais**: O Vertex AI Model Garden disponibiliza tanto a família **Google Gemini** quanto a família **Anthropic Claude** (Claude 3.5 Sonnet, Haiku, Opus) e modelos open-source (Meta Llama 3).
2. **Faturamento Consolidado**: 100% dos custos são debitados diretamente no contrato existente da Light com o Google Cloud (GCP Billing). Não são necessários cartões de crédito corporativos nem assinaturas separadas com a Anthropic.
3. **Privacidade e Residência de Dados**: O tráfego não trafega em servidores públicos de terceiros; a inferência permanece dentro do perímetro de segurança do Google Cloud acordado pela Light.

---

## 🔌 4. Padrão de Comunicação Adotado: HTTP Puro (Opção B)

Para evitar dependências desnecessárias de pacotes como `openai`, `google-genai` ou `anthropic` nos microsserviços, a Light adota o padrão **HTTP REST nativo com `requests`** (ou `httpx`).

### Função Padronizada de Invocação:
```python
import os
import requests

def invocar_gateway(endpoint: str, prompt: str, system_prompt: str = None, user_id: str = None, temperature: float = 0.2) -> str:
    """
    Realiza a chamada direta ao MLflow AI Gateway da Light via HTTP puro.
    
    :param endpoint: Nome do endpoint no Gateway (ex: 'chat-fast', 'code-expert')
    :param prompt: Pergunta ou instrução do usuário
    :param system_prompt: Contexto de sistema
    :param user_id: Matrícula ou identificador do usuário para auditoria
    :param temperature: Determinismo da geração
    """
    base_url = os.getenv("MLFLOW_TRACKING_URI", "").rstrip("/")
    token = os.getenv("MLFLOW_TRACKING_TOKEN") or os.getenv("MLFLOW_API_TOKEN")

    url = f"{base_url}/gateway/endpoints/{endpoint}/invocations"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "messages": messages,
        "temperature": temperature
    }
    if user_id:
        payload["user"] = user_id

    response = requests.post(url, json=payload, headers=headers, timeout=60)
    
    if response.status_code == 429:
        raise RuntimeError(f"Teto de orçamento excedido no MLflow AI Gateway para [{endpoint}] (HTTP 429).")
        
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]
```

---

## 🔑 5. Autenticação, Identidade e Federação com o NAM (SSO Light)

A grande vantagem da infraestrutura da Light é que o **Google Cloud Identity já é federado com o NAM (NetIQ Access Manager) via SAML 2.0**. Quando qualquer usuário tenta logar em um serviço Google com `@light.com.br`, o Google automaticamente delega a autenticação para o NAM corporativo.

### Canais de Acesso e Fluxo de Autenticação:

```
[ Usuário / Desenvolvedor ]
            │
            ▼
[ Google Cloud Identity ] ──(SAML 2.0)──► [ NAM da Light (Matrícula + Senha + MFA) ]
            │                                               │
            │ Retorna com Token Válido                      ▼
            ├───────────────────────────────────────────────┤
            │                                               │
            ▼                                               ▼
   [ Interface Web UI ]                           [ Coding Agents (CLI) ]
   - Usuário abre no Browser                      - Desenvolvedor roda:
   - Google IAP repassa o header:                   'gcloud auth login'
     X-Goog-Authenticated-User-Email              - Token gerado:
   - MLflow sabe quem é a pessoa                   'gcloud auth print-identity-token'
```

### Desmistificação das Licenças de Coding Agents:
* **Claude Code**: **NÃO exige assinatura Claude Pro ($20) nem Max**. 
  O Claude Code suporta oficialmente provedores de terceiros (`CLAUDE_CODE_USE_VERTEX=1`). Quando apontado para o MLflow da Light (`ANTHROPIC_BASE_URL`), ele desvia da tela de login da Anthropic e debita da fatura GCP da Light.
* **Google Antigravity**: Conecta-se diretamente com a conta `@light.com.br` via NAM, consumindo o Vertex AI e os servidores MCP catalogados no MLflow.

---

## 👥 6. Matriz de Governança e Grupos Corporativos (IAM / RBAC)

Para evitar concessão de acessos individuais, a segurança é baseada em **5 Grupos Corporativos (Google Groups)**:

| Grupo | Perfil | Permissões |
| :--- | :--- | :--- |
| **`gcp-mlflow-admins@light.com.br`** | Time Core de IA / MLOps | Gestão total da infraestrutura, Cloud SQL, criação de endpoints e definição de Budgets ($$). |
| **`gcp-mlflow-developers@light.com.br`** | Engenheiros de Software e IA | Acesso ao Claude Code, Antigravity, envio de traces locais e visualização de seus traces. |
| **`gcp-mlflow-prompt-engineers@light.com.br`** | Especialistas de Negócio e QA | Acesso ao **Playground** web do MLflow e **Prompt Registry** para testes sem programar código. |
| **`gcp-mlflow-finops-auditors@light.com.br`** | Controladoria, FinOps e DPO/Segurança | Acesso analítico a relatórios de custos (**Usage**) e auditoria de vazamento de dados (**Traces**). |
| **`gcp-mlflow-viewers@light.com.br`** | Stakeholders e Liderança | Visualização geral de métricas consolidadas. |

> **Aplicações Automatizadas (Chatbots, Jobs ETL)**: Não utilizam grupos humanos. Utilizam **Service Accounts** do GCP (ex: `sa-chatbot-agv@...`) com a role `roles/run.invoker`.

---

## 🌐 7. Topologia de Rede & Regularização da Shared VPC (Caso Sena)

### O Problema Identificado no Ambiente Antigo:
* No Terraform anterior, o recurso `google_compute_network` utilizava `auto_create_subnetworks = true`.
* Isso gerou sub-redes em todas as regiões do mundo no range `10.128.0.0/9`, colidindo (*overlap*) com as faixas de rede internas On-Premise da Light (`10.x.x.x`).
* O Chatbot AGV tomava `403 Forbidden` nas APIs internas (`analisar consumo`, `identPN`) porque o Cloud Run saía para a internet com IPs públicos aleatórios da Google, sendo barrado pelos firewalls e WAF da Light.

### A Solução Definitiva com a Shared VPC:
1. **Eliminar a VPC com auto-subnets**.
2. **Atrelar o projeto do MLflow como Service Project da Shared VPC** gerenciada pelo Sena (Host Project).
3. **Cloud Run com Egress Corporativo**:
   O Cloud Run utiliza o Serverless VPC Access Connector (ou Direct VPC Egress) na subnet autorizada com `egress = "ALL_TRAFFIC"`. Todo o tráfego sai pelo Cloud NAT com IP estático homologado ou via Interconnect direto para as APIs internas da Light.
4. **Cloud SQL Privado**:
   Conecta-se ao range de *Private Services Access (PSA)* alocado na Shared VPC pelo time de redes.

---

## 🏢 8. Estratégia de Projeto Único: O Hub Central Corporativo

Em vez de fragmentar a observabilidade em múltiplos projetos (`mlflow-dev`, `mlflow-hml`, `mlflow-prd`) — o que triplicaria custos de banco, dividiria os dashboards e impediria a promoção de prompts via aliases —, adota-se o modelo **PaaS Centralizado**:

* **Um Único Projeto no GCP**: `light-mlflow-platform` (Hospedando `https://mlflow.light.com.br`).
* **Isolamento de Ambientes por Tags**:
  As aplicações continuam segregadas em seus ambientes normais. Ao reportar dados, o SDK injeta a tag `LIGHT_ENV`:
  ```python
  LightMLflowConfig.setup(experiment_name=f"Chatbot_AGV_{os.getenv('LIGHT_ENV', 'DEV')}")
  ```
* **Atualizações sem Downtime (Cloud Run Revisions)**:
  Atualizações do MLflow são testadas em revisões com 0% de tráfego (Canary). O tráfego só é virado após validação total, permitindo rollback instantâneo se necessário.

---

## 🔀 9. Roteamento Inteligente de Modelos (Model Router & FinOps)

O Gateway expõe **Endpoints Semânticos** baseados em propósito, gerando até **80% de economia financeira**:

```
                       REQUISIÇÃO DA APLICAÇÃO
                                  │
                                  ▼
                    ┌───────────────────────────┐
                    │     Classificador Rápido  │
                    │   (Complexidade do Prompt)│
                    └─────────────┬─────────────┘
                                  │
         ┌────────────────────────┴────────────────────────┐
         ▼ (Simples / FAQ / Atendimento)                   ▼ (Código / Raciocínio Profundo)
┌─────────────────────────────────┐               ┌─────────────────────────────────┐
│ Endpoint: 'chat-fast'           │               │ Endpoint: 'code-expert'         │
│ Modelo: Gemini 2.5 Flash        │               │ Modelo: Claude 3.5 Sonnet       │
│ Custo: ~$0,15 / 1M tokens       │               │ Custo: ~$3,00 / 1M tokens       │
│ Fallback: Claude 3.5 Haiku      │               │ Fallback: Gemini 1.5 Pro        │
└─────────────────────────────────┘               └─────────────────────────────────┘
```

---

## 🛡️ 10. Hardening de Infraestrutura & Resiliência (Cloud SQL & Cloud Run)

Durante a auditoria de saúde do ambiente atual (`light-energia-dev-a39122fa`), foram mapeados pontos de alta prioridade pelo **Google Cloud Security Advisor**. O novo projeto `light-mlflow-platform` já nasce com todos esses hardnings aplicados via Terraform:

### A. Blindagem e Flags do Cloud SQL (PostgreSQL 15)
1. **Criptografia em Trânsito**: `ssl_mode = "ENCRYPTED_ONLY"` forçado no bloco `ip_configuration`, eliminando tráfego não criptografado.
2. **Recuperação Point-in-Time (PITR)**:
   - `point_in_time_recovery_enabled = true` com retenção de logs de transação por 7 dias. Permite restaurar o banco para o estado exato de qualquer minuto específico em caso de desastre.
   - Backup diário automático agendado para as 23:00 BRT (`start_time = "02:00"` UTC).
3. **Auditoria e Diagnóstico de Performance (Database Flags)**:
   - `log_connections = "on"`: Registra auditoria completa de conexões autenticadas.
   - `log_disconnections = "on"`: Rastreia encerramentos anômalos de sessão.
   - `log_min_duration_statement = "2000"`: Grava no Cloud Logging qualquer query que demorar mais de 2 segundos, permitindo caçar gargalos de concorrência em Traces de IA.
4. **Alta Disponibilidade**:
   - `availability_type = "REGIONAL"` para Produção (com réplica de failover automático entre zonas no GCP).

### B. Matriz de Dimensionamento de Infraestrutura

| Componente | Configuração Homologada para a Light | Justificativa |
|---|---|---|
| **Cloud SQL Tier** | `db-custom-2-7680` (2 vCPU, 7.5 GB RAM) | Substitui a frágil `db-f1-micro`, suportando 100k+ traces sem sobrecarga de memória. |
| **Cloud SQL Storage** | 50 GB SSD com auto-increase | Escalabilidade automática conforme os traces se acumulam. |
| **Cloud Run Memory** | 4 a 8 GiB com 4 workers Uvicorn | Permite alta concorrência de chamadas HTTP simultâneas no Gateway. |
| **Cloud Run Scaling** | `min_instances = 2`, `max_instances = 100` | Garante zero cold start para clientes e capacidade de absorver picos de tráfego. |

### C. Mapeamento de Secrets no Secret Manager
No projeto novo, os seguintes segredos devem ser mantidos no **Secret Manager**:
1. `mlflow-db-password`: Senha master do usuário `mlflow_user`.
2. `mlflow-api-token`: Token corporativo unificado compartilhado com os Agentes de IA (`28684e077978582afa...`).
3. `mlflow-backend-store-uri`: Connection string PostgreSQL gerada automaticamente pelo Terraform apontando para o IP privado na Shared VPC.

---

## 📦 11. Estratégia de Repositórios & Autonomia

Para manter **100% da sua autonomia**, sem burocracias de esteiras corporativas e sem expor códigos internos da Light no GitHub público:

```
┌──────────────────────────────────────────────────┐      ┌──────────────────────────────────────────────────┐
│   Repositório 1: 'Renanfavaro1/light-mlflow-sdk' │      │    Repositório 2: 'Renanfavaro1/MLflow_Light'    │
│   (Contém apenas o SDK do cliente Python/Node)   │      │    (Contém a Infraestrutura do Servidor)        │
│   ─────────────────────────────────────────────  │      │    ───────────────────────────────────────────── │
│   • Apenas decoradores (@track_pipeline, etc.)   │      │   • Terraform, Cloud Run, Cloud SQL, VPC         │
│   • Zero senhas, zero Terraform, zero infra      │      │   • Plugin light-auth, scripts ETL               │
│   • Pode ser público ou compartilhado via PAT    │      │   • 100% PRIVADO (acesso estrito)                │
└──────────────────────────────────────────────────┘      └──────────────────────────────────────────────────┘
```

### Instalação pelos Desenvolvedores:
```text
# requirements.txt
light-mlflow @ git+https://github.com/Renanfavaro1/light-mlflow-sdk.git
```

### Build Seguro no Cloud Build (CI/CD):
O token de leitura do GitHub é armazenado no **Google Secret Manager** (`github-mlflow-token`) e injetado em tempo de build via `--build-arg`, sem deixar vestígios na imagem final do container.

## 🛡️ 11. AI Firewall & Policy Enforcement no MLflow (Zero Vendor Lock-in)

Para evitar qualquer dependência de ferramentas de nuvem específicas (como Cloud Build ou Cloud Run), **a governança e a aplicação das normas da Light residem 100% dentro do MLflow AI Gateway**.

Como o Gateway é o ponto de passagem obrigatório para todas as inferências de IA, **100% das requisições HTTP são interceptadas, avaliadas e enriquecidas com as normas corporativas**, independentemente de onde a aplicação ou o desenvolvedor esteja rodando (AWS, Azure, On-premise ou laptop local).

```
                        QUALQUER APLICAÇÃO OU DESENVOLVEDOR
                    (AWS, Azure, Databricks, On-premise ou Laptop)
                                       │
                                       │ POST /gateway/endpoints/.../invocations
                                       ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                         MLFLOW AI GATEWAY (Camada de Governança)                       │
│                                                                                        │
│ 1. O Prompt Registry armazena o Markdown das Normas da Light:                          │
│    📄 'light-corporate-guidelines@production'                                         │
│                                                                                        │
│ 2. BEFORE-GUARDRAILS (Avaliação e Injeção em Tempo Real):                              │
│    • Injeção Mandatória: Se a requisição não possui system prompt, o Gateway injeta    │
│      as normas da Light como mensagem 'system' primária.                               │
│    • Inspeção de Entrada (DLP / Anti-Injection): Se o prompt contiver tentativa de     │
│      jailbreak, vazamento de chaves ou violação ética ➔ Bloqueio imediato (HTTP 403).  │
│                                                                                        │
│ 3. ENCAMINHAMENTO SEGURO AO MODELO:                                                    │
│    • Apenas prompts validados e enquadrados nas normas chegam ao Google Vertex AI.     │
│                                                                                        │
│ 4. AFTER-GUARDRAILS (Avaliação da Resposta):                                           │
│    • Inspeciona a resposta do modelo para garantir conformidade antes de retornar.     │
└──────────────────────────────────────┬─────────────────────────────────────────────────┘
                                       │
                                       ▼
                         [ Google Vertex AI / Modelos ]
```

### Principais Vantagens dessa Abordagem:
1. **Zero Vendor Lock-in**: Não importa se o dev usa Jenkins, GitLab CI, GitHub Actions ou executa no terminal local: a regra de negócio da Light é aplicada na borda do MLflow.
2. **Atualização Centralizada em Tempo Real**:
   Quando a Light atualizar uma diretriz de arquitetura ou segurança, você edita o Markdown **apenas no Prompt Registry do MLflow**. No segundo seguinte, o Claude Code e os chatbots de toda a companhia já passam a seguir a nova diretriz, sem necessidade de rebuild ou redeploy de código.
3. **Economia Financeira Ativa**:
   Requisições com tentativas de jailbreak ou prompts fora do padrão são descartadas com `HTTP 403` **antes** de consumir tokens dos modelos da Google/Anthropic.

---

## 💰 12. FinOps, Rateio Contábil & Governança Desacoplada (Databricks + Painel_Mlflow)

Para garantir flexibilidade total e evitar retrabalho, **a regra de negócio e o rateio por Centro de Custos ficam 100% DESACOPLADOS do MLflow e do código das aplicações**.

Em grandes empresas como a Light, colaboradores mudam de setor e projetos trocam de donos orçamentários com frequência. Se o Centro de Custo estivesse chumbado no MLflow ou nas aplicações, qualquer reorganização exigiria refatoração e novos deploys.

### A Arquitetura Dimensional (Star Schema):
Adotamos o padrão clássico de Engenharia de Dados: o MLflow registra apenas **fatos técnicos imutáveis**, e o Databricks realiza o **JOIN relacional dinâmico** com as tabelas de cadastro corporativo.

```
┌────────────────────────────────────────────────────────┐
│           MLFLOW (Apenas os Fatos Técnicos)            │
│  • application_name (ex: 'Chatbot_AGV')                │
│  • user_id / matricula (ex: '4013895')                 │
│  • tokens, timestamp, custo em USD                     │
└───────────────────────────┬────────────────────────────┘
                            │ (ETL Diário às 03:00 - Parquet)
                            ▼
┌────────────────────────────────────────────────────────┐
│               DATABRICKS UNITY CATALOG                 │
│                                                        │
│  Tabela de Fatos:       Tabelas Dimensão (De-Para):    │
│  [ mlflow_runs ]  ──►   [ dim_colaboradores ]          │
│  (matricula, app) ──►   (matricula -> Centro de Custo) │
│                         [ dim_aplicacoes ]             │
│                         (app_name -> Centro de Custo)  │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│      PAINEL MLFLOW LIGHT (Databricks Apps)             │
│  • Localização: 'C:\Users\4013895\Painel_Mlflow'       │
│  • JOIN dinâmico em tempo de execução                  │
│  • Gestão de De-Para e relatórios contábeis para o SAP │
│  • Se o dev mudar de gerência, altera 1 linha no BD!   │
└────────────────────────────────────────────────────────┘
```

### 1. Dados Registrados no MLflow (Sem Acoplamento de Negócio):
* `app_name`: Nome da aplicação/experimento (ex: `Chatbot_AGV`, `Veritas`, `Normas_BT`).
* `user_id`: Matrícula corporativa do usuário (ex: `4013895`).
* `tokens`, `latência` e `custo_usd`.

### 2. Tabelas de Dimensão no Databricks Unity Catalog:
* **`dim_colaboradores`** (Para Claude Code / Coding Agents):
  `matricula` | `nome` | `gerencia` | `centro_de_custo` | `diretoria`
* **`dim_aplicacoes`** (Para Chatbots e APIs em Produção):
  `app_name` | `squad` | `gerencia_dona` | `centro_de_custo`

### 3. Consulta de Rateio Dinâmico no `Painel_Mlflow`:
```sql
SELECT 
    COALESCE(u.centro_de_custo, a.centro_de_custo, 'CENTRO_DE_CUSTO_GERAL') AS centro_de_custo,
    COALESCE(u.gerencia, a.gerencia_dona, 'GERENCIA_GERAL') AS gerencia,
    r.experiment_name AS ferramenta_ou_dev,
    COUNT(r.run_uuid) AS total_interacoes,
    SUM(r.total_tokens) AS volume_tokens,
    ROUND(SUM(r.cost_usd) * 5.75, 2) AS valor_rateio_brl
FROM mlflow_light_dev.runs r
LEFT JOIN mlflow_light_dev.dim_colaboradores u ON r.user_id = u.matricula
LEFT JOIN mlflow_light_dev.dim_aplicacoes a ON r.experiment_name = a.app_name
WHERE r.start_time >= DATE_TRUNC('month', CURRENT_DATE())
GROUP BY 1, 2, 3
ORDER BY valor_rateio_brl DESC;
```

### Benefícios Práticos:
* **Manutenção Instantânea**: Um colaborador mudou de gerência? Basta atualizar o registro dele na tabela do Databricks (ou via tela de cadastro no painel). O rateio do mês seguinte sai recalculado sem tocar em nenhuma linha de código.
* **Autonomia e Transparência**: O gestor do Centro de Custos de IA extrai mensalmente o relatório do Databricks Apps e envia à Controladoria da Light para efetuar o débito/crédito interno no SAP.

---

## 🔌 13. Catálogo de Ferramentas Corporativas (MCP Registry para SAP & Databricks)

O MLflow 3.15 atua como o **Catálogo Corporativo de Ferramentas de IA (MCP Hub)** através da aba **`MCP registry`**:

```
[ Agentes / Claude Code / Antigravity ]
                   │
                   ▼ 1. Descobrem Ferramentas Homologadas
┌────────────────────────────────────────────────────────┐
│                 MLFLOW MCP REGISTRY                    │
│  • mcp-server-sap        ➔ Faturamento, 2ª via, corte  │
│  • mcp-server-databricks ➔ Queries no Lakehouse Unity  │
│  • mcp-server-normas     ➔ RAG de Normas RECON-BT      │
└──────────────────┬─────────────────────────────────────┘
                   │
                   ▼ 2. Executam com Governança e Segurança
┌────────────────────────────────────────────────────────┐
│             SISTEMAS CORPORATIVOS DA LIGHT             │
│  (SAP On-Premise via Shared VPC | Databricks Lakehouse)│
└────────────────────────────────────────────────────────┘
```

* **Construa 1 vez, use em todos os agentes**: A squad de faturamento desenvolve o conector SAP uma única vez no padrão MCP. Todos os chatbots e desenvolvedores passam a usá-lo imediatamente.
* **Eliminação de Alucinação**: Modelos não inventam regras ou valores de faturas; são obrigados a consultar ferramentas oficiais.

---

## 🧱 14. Conformidade com a "Chinese Wall" da Light (Segurança e ANEEL)

A arquitetura foi concebida para atender estritamente aos dois pilares da política de **Muralha da China (Chinese Wall)** da Light:

### A. Chinese Wall de Perímetro e Rede (Fim do Erro 403)
* A Chinese Wall de TI bloqueia qualquer requisição vinda da internet pública sem IP homologado.
* **A Solução**: O Cloud Run conecta-se à **Shared VPC do Sena com `egress = "ALL_TRAFFIC"`**. O tráfego atinge a barreira de segurança com IP corporativo validado, liberando o acesso às APIs do SAP e sistemas comerciais.

### B. Chinese Wall Regulatória (ANEEL)
* A ANEEL proíbe expressamente o cruzamento ou vazamento de informações entre a **Distribuidora (Mercado Regulado)** e a **Comercializadora (Mercado Livre)**.
* **A Solução**: Mascaramento estrito de dados de identificação (LGPD/PII) e segregação lógica de experimentos (`dist_...` vs `comerc_...`) com controle de acesso granular via Google Groups.

---

## 🚀 15. Plano de Ação Passo a Passo (Roadmap de Implantação)

Siga este checklist sequencial para executar o projeto com excelência:

### Etapa 1: Solicitações Formais de Infraestrutura (GCP & IAM)
- [ ] **Criar o Projeto no GCP**: Solicitar a criação do projeto corporativo **`light-mlflow-platform`**.
- [ ] **Criar os 5 Grupos no Google Cloud Identity / NAM**:
  - `gcp-mlflow-admins@light.com.br`
  - `gcp-mlflow-developers@light.com.br`
  - `gcp-mlflow-prompt-engineers@light.com.br`
  - `gcp-mlflow-finops-auditors@light.com.br`
  - `gcp-mlflow-viewers@light.com.br`
- [ ] **Habilitar as APIs no Projeto**:
  - `run.googleapis.com` (Cloud Run)
  - `sqladmin.googleapis.com` (Cloud SQL)
  - `secretmanager.googleapis.com` (Secret Manager)
  - `vpcaccess.googleapis.com` (VPC Access)
  - `compute.googleapis.com` (Compute Engine)
  - `aiplatform.googleapis.com` (Vertex AI)

### Etapa 2: Alinhamento com a Equipe de Redes (Thiago Sena)
- [ ] Enviar a solicitação ao Sena solicitando:
  1. Associação do projeto `light-mlflow-platform` como **Service Project** na Shared VPC da Light.
  2. Nome do **Serverless VPC Access Connector** (ou sub-rede autorizada para Direct VPC Egress).
  3. Confirmação do range alocado para **Private Services Access (PSA)** para o Cloud SQL privado.
  4. Concessão de `roles/vpcaccess.user` para a Service Account padrão do Cloud Run do projeto.

### Etapa 3: Higienização e Refatoração do Terraform
- [ ] Remover o módulo `infrastructure/modules/networking` antigo com `auto_create_subnetworks = true`.
- [ ] Atualizar o módulo `infrastructure/modules/cloud_sql` para apontar `private_network` para a Shared VPC corporativa.
- [ ] Adicionar no Cloud SQL:
  - `ssl_mode = "ENCRYPTED_ONLY"`
  - `point_in_time_recovery_enabled = true`
  - Flags: `log_connections = "on"`, `log_disconnections = "on"`, `log_min_duration_statement = "2000"`
  - Máquina `db-custom-2-7680` (2 vCPUs, 7.5GB RAM).
- [ ] Atualizar o módulo `infrastructure/modules/cloud_run` para usar o conector do Sena com `egress = "ALL_TRAFFIC"` e `4 workers` Uvicorn.

### Etapa 4: Separação dos Repositórios no GitHub
- [ ] Criar o repositório **`Renanfavaro1/light-mlflow-sdk`** na sua conta pessoal.
- [ ] Mover as pastas `sdk/` e `sdk-node/` para esse novo repositório.
- [ ] Tornar o repositório de infraestrutura **`Renanfavaro1/MLflow_Light`** totalmente **Privado**.

### Etapa 5: Deploy do Ambiente e Migração dos Dados
- [ ] Criar os Secrets no novo projeto: `mlflow-db-password` e `mlflow-api-token`.
- [ ] Executar o backup do PostgreSQL atual do projeto legado (`light-energia-dev-a39122fa`):
  ```bash
  gcloud sql export sql mlflow-db-instance gs://SEU_BUCKET_TRANSICAO/mlflow_dump_backup.sql \
    --database=mlflow \
    --project=light-energia-dev-a39122fa
  ```
- [ ] Rodar o `terraform apply` no projeto `light-mlflow-platform`.
- [ ] Restaurar o banco de dados na nova instância do Cloud SQL:
  ```bash
  gcloud sql import sql mlflow-db-instance gs://SEU_BUCKET_TRANSICAO/mlflow_dump_backup.sql \
    --database=mlflow \
    --project=light-mlflow-platform
  ```
- [ ] Sincronizar os artefatos históricos do GCS:
  ```bash
  gcloud storage rsync -r gs://mlflow-artifacts-light-energia-dev-a39122fa gs://mlflow-artifacts-light-mlflow-platform
  ```
- [ ] Fazer o deploy do container do MLflow Server no Cloud Run.

### Etapa 6: Configuração do AI Gateway e Prompt Registry no MLflow
- [ ] Acessar o novo painel do MLflow (`https://mlflow...`).
- [ ] Na aba **AI Gateway > Endpoints**, criar os endpoints:
  - `chat-fast` ➔ `gemini-2.5-flash`
  - `code-expert` ➔ `claude-3-5-sonnet` (Vertex AI)
  - `deep-context` ➔ `gemini-1.5-pro`
- [ ] Na aba **Budgets**, definir as políticas de teto financeiro mensal.
- [ ] Na aba **Prompts**, registrar o Markdown oficial de normas da Light (`light-corporate-guidelines`) com a tag `@production`.
- [ ] Habilitar os **Gateway Guardrails** vinculando o prompt às rotas de inferência.

### Etapa 7: Configuração de FinOps & Rateio no Databricks
- [ ] Criar as tabelas de dimensão `dim_colaboradores` e `dim_aplicacoes` no Unity Catalog.
- [ ] Habilitar a tela de rateio no **`Painel_Mlflow`** (Databricks Apps) conectada à view de rateio.

### Etapa 8: Validação e Homologação
- [ ] Testar autenticação web via NAM.
- [ ] Testar execução do **Claude Code** no terminal apontando para o Gateway (validando a injeção automática das normas).
- [ ] Testar chamada de inferência pelo **Chatbot AGV** via Shared VPC (confirmando o fim do erro 403 nas APIs internas).

### Etapa 9: Descomissionamento do Ambiente Antigo
- [ ] Rodar `terraform destroy` no ambiente antigo (eliminando as VPCs antigas que causavam overlap com o on-premise).
- [ ] Notificar o Sena que a rede antiga foi 100% desprovisionada.
