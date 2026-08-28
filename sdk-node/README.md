# SDK Light MLflow (Node.js)

Pacote oficial da Light para observabilidade de Inteligência Artificial Generativa e tracking em backends JavaScript / TypeScript (Express, NestJS, Vite SSR, Fastify).

## 🚀 Instalação

```bash
npm install git+https://github.com/Renanfavaro1/MLflow_Light.git#subdirectory=sdk-node
```

## ⚙️ Configuração Básica

```javascript
import { LightMLflowConfig, trackPipeline, llmSpan } from 'light-mlflow-node';

// Inicializa lendo MLFLOW_TRACKING_URI e MLFLOW_TRACKING_TOKEN do ambiente
await LightMLflowConfig.setup("Meu_Projeto_Node");

const chamarIA = llmSpan("Gemini_Chat", async (prompt) => {
    // Sua lógica com @google/genai ou openai
    return response;
});

const endpointAtendimento = trackPipeline("Atendimento_Chat", async (req) => {
    return await chamarIA(req.body.mensagem);
});
```

## 🛡️ Destaques
- **Fail-Safe**: Se a conexão falhar, a requisição do usuário prossegue sem erro.
- **OpenTelemetry Integrado**: Rastreamento OTLP nativo para a aba Traces do MLflow.
