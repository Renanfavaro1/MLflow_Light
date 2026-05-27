import MLflowClient from './client.js';
import opentelemetry from '@opentelemetry/api';
import { NodeTracerProvider } from '@opentelemetry/sdk-trace-node';
import { BatchSpanProcessor } from '@opentelemetry/sdk-trace-base';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';
import { Resource } from '@opentelemetry/resources';

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

            // Configurar OpenTelemetry para Traces
            const cleanUri = trackingUri.endsWith('/') ? trackingUri.slice(0, -1) : trackingUri;
            const otlpUrl = process.env.OTEL_EXPORTER_OTLP_TRACES_ENDPOINT || `${cleanUri}/v1/traces`;

            const provider = new NodeTracerProvider({
                resource: new Resource({
                    'service.name': experimentName,
                }),
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

            // Usamos BatchSpanProcessor para performance, mas com flush rápido se necessário
            provider.addSpanProcessor(new BatchSpanProcessor(exporter));
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
