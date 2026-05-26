import { AsyncLocalStorage } from 'node:async_hooks';
import LightMLflowConfig from './config.js';

// Armazenamento assíncrono para manter o contexto da Execução (Run) entre diferentes funções assíncronas.
export const runStorage = new AsyncLocalStorage();

/**
 * Wrapper principal que cria a Execução no MLflow e injeta o ID no contexto.
 */
export function trackPipeline(runName, asyncFunc) {
    return async function (...args) {
        if (!LightMLflowConfig.client || !LightMLflowConfig.experimentId) {
            return await asyncFunc(...args);
        }

        let runId = null;
        try {
            runId = await LightMLflowConfig.client.createRun(LightMLflowConfig.experimentId, runName);
        } catch (e) {
            console.warn(`Aviso: falha ao iniciar run ${runName}`, e.message);
            return await asyncFunc(...args);
        }
        
        return await runStorage.run(runId, async () => {
            try {
                const result = await asyncFunc(...args);
                await LightMLflowConfig.client.updateRun(runId, "FINISHED");
                return result;
            } catch (e) {
                await LightMLflowConfig.client.updateRun(runId, "FAILED");
                throw e;
            }
        });
    }
}

/**
 * Wrapper para chamadas de LLM. Extrai tokens magicamente e envia para o Run ativo.
 */
export function llmSpan(spanName, asyncFunc) {
    return async function (...args) {
        const runId = runStorage.getStore();
        if (!runId || !LightMLflowConfig.client) {
            return await asyncFunc(...args);
        }

        const response = await asyncFunc(...args);
        _extractAndLogTokens(runId, response);
        return response;
    }
}

function _extractAndLogTokens(runId, response) {
    try {
        if (response && response.usageMetadata) {
            const usage = response.usageMetadata;
            const p = usage.promptTokenCount || 0;
            const c = usage.candidatesTokenCount || 0;
            const t = usage.totalTokenCount || (p + c);
            
            if (t > 0) {
                LightMLflowConfig.client.logMetric(runId, "llm.usage.prompt_tokens", p);
                LightMLflowConfig.client.logMetric(runId, "llm.usage.completion_tokens", c);
                LightMLflowConfig.client.logMetric(runId, "llm.usage.total_tokens", t);
            }
        }
        // Suporte para o SDK Oficial da OpenAI Node.js
        else if (response && response.usage) {
            const usage = response.usage;
            const p = usage.prompt_tokens || 0;
            const c = usage.completion_tokens || 0;
            const t = usage.total_tokens || (p + c);

            if (t > 0) {
                LightMLflowConfig.client.logMetric(runId, "llm.usage.prompt_tokens", p);
                LightMLflowConfig.client.logMetric(runId, "llm.usage.completion_tokens", c);
                LightMLflowConfig.client.logMetric(runId, "llm.usage.total_tokens", t);
            }
        }
    } catch (e) {
        console.warn("Aviso: Falha ao extrair métricas de tokens da resposta", e.message);
    }
}
