import { LightMLflowConfig, trackPipeline, llmSpan, toolSpan } from '../sdk-node/src/index.js';

// Simulando a variável de ambiente (geralmente injetada pelo Cloud Run)
process.env.MLFLOW_TRACKING_URI = "https://mlflow-tracking-server-lvvvhziq5a-uc.a.run.app";

console.log("Iniciando Setup...");
await LightMLflowConfig.setup("Light_Node_Traces_Test");

const mockTool = toolSpan("Buscar_Dados_SAP", async (id) => {
    console.log(`[Tool] Buscando dados para id: ${id}...`);
    await new Promise(r => setTimeout(r, 500));
    return { status: "success", data: "Cliente SAP OK" };
});

const mockLLM = llmSpan("Gemini_Mock", async (prompt, context) => {
    console.log("[LLM] Gerando resposta...");
    await new Promise(r => setTimeout(r, 1000));
    return {
        text: `Resposta para: ${prompt}. Contexto: ${JSON.stringify(context)}`,
        usageMetadata: {
            promptTokenCount: 150,
            candidatesTokenCount: 80,
            totalTokenCount: 230
        }
    };
});

const processarMensagem = trackPipeline("Atendimento_Teste_Trace", async (pergunta, userId) => {
    const sapData = await mockTool(userId);
    const resposta = await mockLLM(pergunta, sapData);
    return resposta;
});

console.log("Iniciando Pipeline...");
const res = await processarMensagem("Como está minha fatura?", "12345");
console.log("Resultado final:", res);

console.log("Aguardando 6s para flush dos traces...");
await new Promise(r => setTimeout(r, 6000));
console.log("Teste finalizado. Verifique a aba Traces no MLflow!");
