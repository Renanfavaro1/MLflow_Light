import { AsyncLocalStorage } from 'node:async_hooks';
import LightMLflowConfig from './config.js';
import opentelemetry from '@opentelemetry/api';

// Armazenamento assíncrono para manter o contexto da Execução (Run) entre diferentes funções assíncronas.
export const runStorage = new AsyncLocalStorage();

/**
 * Função interna para gerenciar spans genéricos no OpenTelemetry
 */
async function _traceWithSpan(spanName, spanType, asyncFunc, args) {
    const runId = runStorage.getStore();
    if (!runId || !LightMLflowConfig.tracer) {
        return await asyncFunc(...args);
    }

    const span = LightMLflowConfig.tracer.startSpan(spanName, {
        attributes: {
            'mlflow.run_id': String(runId),
            'mlflow.spanType': spanType,
        }
    });

    const otelCtx = opentelemetry.trace.setSpan(opentelemetry.context.active(), span);

    return await opentelemetry.context.with(otelCtx, async () => {
        span.setAttribute('mlflow.spanInputs', JSON.stringify(_safeSerialize({ args })));
        try {
            const result = await asyncFunc(...args);
            span.setAttribute('mlflow.spanOutputs', JSON.stringify(_safeSerialize(result)));
            span.setStatus({ code: opentelemetry.SpanStatusCode.OK });
            return result;
        } catch (e) {
            span.setStatus({
                code: opentelemetry.SpanStatusCode.ERROR,
                message: e.message
            });
            throw e;
        } finally {
            span.end();
        }
    });
}

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

        const runCode = async () => {
            if (LightMLflowConfig.tracer) {
                const span = LightMLflowConfig.tracer.startSpan(runName, {
                    attributes: {
                        'mlflow.run_id': String(runId),
                        'mlflow.spanType': 'CHAIN',
                    }
                });
                const otelCtx = opentelemetry.trace.setSpan(opentelemetry.context.active(), span);

                return await opentelemetry.context.with(otelCtx, async () => {
                    span.setAttribute('mlflow.spanInputs', JSON.stringify(_safeSerialize({ args })));
                    try {
                        const result = await asyncFunc(...args);
                        span.setAttribute('mlflow.spanOutputs', JSON.stringify(_safeSerialize(result)));
                        span.setStatus({ code: opentelemetry.SpanStatusCode.OK });
                        await LightMLflowConfig.client.updateRun(runId, "FINISHED");
                        return result;
                    } catch (e) {
                        span.setStatus({
                            code: opentelemetry.SpanStatusCode.ERROR,
                            message: e.message
                        });
                        await LightMLflowConfig.client.updateRun(runId, "FAILED");
                        throw e;
                    } finally {
                        span.end();
                    }
                });
            } else {
                try {
                    const result = await asyncFunc(...args);
                    await LightMLflowConfig.client.updateRun(runId, "FINISHED");
                    return result;
                } catch (e) {
                    await LightMLflowConfig.client.updateRun(runId, "FAILED");
                    throw e;
                }
            }
        };
        
        return await runStorage.run(runId, runCode);
    }
}

/**
 * Wrapper para chamadas de LLM. Extrai tokens e envia para o Run ativo e Span do OpenTelemetry.
 */
export function llmSpan(spanName, asyncFunc) {
    return async function (...args) {
        const runId = runStorage.getStore();
        if (!runId || !LightMLflowConfig.client) {
            return await asyncFunc(...args);
        }

        if (LightMLflowConfig.tracer) {
            const span = LightMLflowConfig.tracer.startSpan(spanName, {
                attributes: {
                    'mlflow.run_id': String(runId),
                    'mlflow.spanType': 'LLM',
                }
            });
            const otelCtx = opentelemetry.trace.setSpan(opentelemetry.context.active(), span);

            return await opentelemetry.context.with(otelCtx, async () => {
                try {
                    const response = await asyncFunc(...args);
                    _extractAndLogTokens(runId, response, span);

                    const { normIn, normOut } = _normalizeLlmSpanData(args, response);
                    if (normIn && normOut) {
                        span.setAttribute('mlflow.spanInputs', JSON.stringify(normIn));
                        span.setAttribute('mlflow.spanOutputs', JSON.stringify(normOut));
                    } else {
                        span.setAttribute('mlflow.spanInputs', JSON.stringify(_safeSerialize({ args })));
                        span.setAttribute('mlflow.spanOutputs', JSON.stringify(_safeSerialize(response)));
                    }

                    span.setStatus({ code: opentelemetry.SpanStatusCode.OK });
                    return response;
                } catch (e) {
                    span.setStatus({
                        code: opentelemetry.SpanStatusCode.ERROR,
                        message: e.message
                    });
                    throw e;
                } finally {
                    span.end();
                }
            });
        } else {
            const response = await asyncFunc(...args);
            _extractAndLogTokens(runId, response);
            return response;
        }
    }
}

/**
 * Wrapper para ferramentas / tools consumidas por agentes.
 */
export function toolSpan(spanName, asyncFunc) {
    return async function (...args) {
        return await _traceWithSpan(spanName, 'TOOL', asyncFunc, args);
    }
}

/**
 * Wrapper para recuperação de dados de contexto (retriever).
 */
export function retrieverSpan(spanName, asyncFunc) {
    return async function (...args) {
        return await _traceWithSpan(spanName, 'RETRIEVER', asyncFunc, args);
    }
}

/**
 * Wrapper para encapsular lógica interna do agente.
 */
export function agentSpan(spanName, asyncFunc) {
    return async function (...args) {
        return await _traceWithSpan(spanName, 'AGENT', asyncFunc, args);
    }
}

function _extractAndLogTokens(runId, response, span = null) {
    try {
        let p = 0, c = 0, t = 0;
        if (response && response.usageMetadata) {
            const usage = response.usageMetadata;
            p = usage.promptTokenCount || 0;
            c = usage.candidatesTokenCount || 0;
            t = usage.totalTokenCount || (p + c);
        }
        // Suporte para o SDK Oficial da OpenAI Node.js
        else if (response && response.usage) {
            const usage = response.usage;
            p = usage.prompt_tokens || 0;
            c = usage.completion_tokens || 0;
            t = usage.total_tokens || (p + c);
        }

        if (t > 0) {
            LightMLflowConfig.client.logMetric(runId, "llm.usage.prompt_tokens", p);
            LightMLflowConfig.client.logMetric(runId, "llm.usage.completion_tokens", c);
            LightMLflowConfig.client.logMetric(runId, "llm.usage.total_tokens", t);

            if (span) {
                span.setAttribute('llm.usage.prompt_tokens', p);
                span.setAttribute('llm.usage.completion_tokens', c);
                span.setAttribute('llm.usage.total_tokens', t);
            }
        }
    } catch (e) {
        console.warn("Aviso: Falha ao extrair métricas de tokens da resposta", e.message);
    }
}

function _safeSerialize(obj) {
    const seen = new WeakSet();
    const serializer = (key, value) => {
        if (typeof value === 'object' && value !== null) {
            if (seen.has(value)) {
                return '[Circular]';
            }
            seen.add(value);
        }
        if (value instanceof Uint8Array || (typeof Buffer !== 'undefined' && Buffer.isBuffer(value))) {
            return '<bytes_data>';
        }
        return value;
    };
    try {
        return JSON.parse(JSON.stringify(obj, serializer));
    } catch (e) {
        return String(obj);
    }
}

function _normalizeLlmSpanData(args, response) {
    const normalizedInputs = { messages: [] };
    const normalizedOutputs = { choices: [{ message: { role: 'assistant', content: '', tool_calls: [] } }] };

    try {
        const contents = args[0];
        if (typeof contents === 'string') {
            normalizedInputs.messages.push({ role: 'user', content: contents });
        } else if (Array.isArray(contents)) {
            for (const c of contents) {
                let role = c.role || 'user';
                if (role === 'model') role = 'assistant';

                let textContent = '';
                const parts = c.parts || [];
                for (const p of parts) {
                    if (p.text) {
                        textContent += p.text;
                    } else if (p.functionResponse) {
                        textContent += `\n[Function Response: ${p.functionResponse.name} -> ${JSON.stringify(p.functionResponse.response)}]`;
                    }
                }
                normalizedInputs.messages.push({ role, content: textContent.trim() });
            }
        }

        if (response && response.text) {
            normalizedOutputs.choices[0].message.content = response.text;
        } else if (response && response.candidates && response.candidates[0]) {
            const cand = response.candidates[0];
            if (cand.content) {
                let outText = '';
                const toolCalls = [];
                const parts = cand.content.parts || [];
                for (const p of parts) {
                    if (p.text) {
                        outText += p.text;
                    } else if (p.functionCall) {
                        const fc = p.functionCall;
                        const argsStr = fc.args ? JSON.stringify(fc.args) : '{}';
                        toolCalls.push({
                            type: 'function',
                            function: {
                                name: fc.name,
                                arguments: argsStr
                            }
                        });
                    }
                }
                normalizedOutputs.choices[0].message.content = outText.trim();
                if (toolCalls.length > 0) {
                    normalizedOutputs.choices[0].message.tool_calls = toolCalls;
                }
            }
        }

        if (response && response.usageMetadata) {
            const usg = response.usageMetadata;
            normalizedOutputs.usage = {
                prompt_tokens: usg.promptTokenCount || 0,
                completion_tokens: usg.candidatesTokenCount || 0,
                total_tokens: usg.totalTokenCount || 0
            };
        }

        return { normIn: normalizedInputs, normOut: normalizedOutputs };
    } catch (e) {
        return { normIn: null, normOut: null };
    }
}
