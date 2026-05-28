import MLflowClient from './client.js';
import opentelemetry from '@opentelemetry/api';
import { NodeTracerProvider } from '@opentelemetry/sdk-trace-node';
import { SimpleSpanProcessor, SamplingDecision } from '@opentelemetry/sdk-trace-base';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';
import { Resource } from '@opentelemetry/resources';
import { AsyncLocalStorage } from 'node:async_hooks';

export const runStorage = new AsyncLocalStorage();

class MLflowSampler {
    shouldSample(context, traceId, spanName, spanKind, attributes, links) {
        // Se há um runId ativo no local storage (ou seja, dentro de trackPipeline), sampleamos.
        // Spans gerados por outras bibliotecas (como Firestore/GCS) fora do trackPipeline são descartados.
        const runId = runStorage.getStore();
        if (runId) {
            return { decision: SamplingDecision.RECORD_AND_SAMPLE };
        }
        return { decision: SamplingDecision.NOT_RECORD };
    }

    toString() {
        return 'MLflowSampler';
    }
}


class LightMLflowConfig {
    static experimentId = null;
    static client = null;
    static tracer = null;
    static provider = null;

    static async setup(experimentName) {
        const trackingUri = process.env.MLFLOW_TRACKING_URI;
        if (!trackingUri) {
            console.warn("Aviso: MLFLOW_TRACKING_URI não definida. O MLflow Node não gravará dados.");
            return;
        }

        this.client = new MLflowClient(trackingUri);
        
        try {
            let exp = await this.client.getExperimentByName(experimentName);
            if (exp) {
                this.experimentId = exp.experiment_id;
            } else {
                this.experimentId = await this.client.createExperiment(experimentName);
            }
            console.log(`✅ MLflow Tracking URI configurado para: ${trackingUri}`);
            console.log(`✅ Experimento ativo: ${experimentName}`);

            // Habilitar logs de diagnóstico internos do OpenTelemetry para capturar erros silenciosos de rede/exportação
            opentelemetry.diag.setLogger(
                new opentelemetry.DiagConsoleLogger(),
                opentelemetry.DiagLogLevel.INFO
            );

            // Configurar OpenTelemetry para Traces
            const cleanUri = trackingUri.endsWith('/') ? trackingUri.slice(0, -1) : trackingUri;
            const otlpUrl = process.env.OTEL_EXPORTER_OTLP_TRACES_ENDPOINT || `${cleanUri}/v1/traces`;

            const provider = new NodeTracerProvider({
                resource: new Resource({
                    'service.name': experimentName,
                }),
                sampler: new MLflowSampler(),
            });

            const exporter = new OTLPTraceExporter({
                url: otlpUrl,
                headers: {
                    'x-mlflow-experiment-id': String(this.experimentId),
                },
                httpAgentOptions: {
                    rejectUnauthorized: false,
                },
            });

            // Usamos SimpleSpanProcessor para flush imediato dos spans no encerramento de cada bloco,
            // garantindo o envio sem depender de timers ou sofrer com o ciclo de vida do Cloud Run.
            provider.addSpanProcessor(new SimpleSpanProcessor(exporter));
            provider.register();

            this.provider = provider;
            this.tracer = opentelemetry.trace.getTracer('light-mlflow-node');
            console.log(`✅ OpenTelemetry Tracer inicializado para o endpoint: ${otlpUrl}`);
        } catch (e) {
            console.error("❌ Erro ao configurar MLflow:", e.message);
        }
    }
}

export default LightMLflowConfig;
