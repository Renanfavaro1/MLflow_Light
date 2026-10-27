import { LightMLflowConfig, trackPipeline, llmSpan } from '../sdk-node/src/index.js';

// Simulando a variável de ambiente (geralmente injetada pelo Cloud Run)
process.env.MLFLOW_TRACKING_URI = process.env.MLFLOW_TRACKING_URI || "https://mlflow-tracking-server-504082412074.us-central1.run.app";
process.env.MLFLOW_TRACKING_TOKEN = process.env.MLFLOW_TRACKING_TOKEN || "28684e077978582afa70be269dbdac57544aae36fb051fa3dc049f2e1c7defd0";

// 1. Inicializa (deve ser feito apenas 1 vez na inicialização da aplicação)
await LightMLflowConfig.setup("Light_Node_APIs");

// 2. Simula uma chamada à LLM que retorna uso de tokens (estilo SDK do Google GenAI para Node)
const gerarRespostaLLM = llmSpan("Gemini_NodeJS", async (prompt) => {
    console.log("Chamando a API do Gemini...");
    // Simulando delay de rede
    await new Promise(r => setTimeout(r, 1000));
    
    // Simulando objeto de resposta da API do Google GenAI (node)
    return {
        text: "Resposta simulada",
        usageMetadata: {
            promptTokenCount: 120,
            candidatesTokenCount: 50,
            totalTokenCount: 170
        }
    };
});

// 3. Orquestrador Principal (Endpoint do Backend)
const processarMensagem = trackPipeline("Atendimento_Cliente", async (pergunta) => {
    const resposta = await gerarRespostaLLM(pergunta);
    return resposta;
});

// 4. Teste de execução
console.log("Iniciando processamento...");
const resultado = await processarMensagem("Olá, minha conta de luz está muito cara.");
console.log("Concluído. Verifique o painel do MLflow na aba 'Metrics' do experimento 'Light_Node_APIs'.");
