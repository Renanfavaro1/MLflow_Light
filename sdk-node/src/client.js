import axios from 'axios';
import https from 'https';

let cachedToken = null;
let tokenExpiry = 0;

/**
 * Obtém o Google ID Token automaticamente do Metadata Server do Cloud Run ou do ambiente.
 */
export async function getGoogleIdToken(audience) {
    if (!audience) return null;

    // 1. Se já fornecido manualmente via variável de ambiente
    if (process.env.MLFLOW_TRACKING_TOKEN) {
        return process.env.MLFLOW_TRACKING_TOKEN;
    }

    // 2. Retorna token em cache se válido por mais de 5 minutos
    const now = Date.now();
    if (cachedToken && tokenExpiry > now + 5 * 60 * 1000) {
        return cachedToken;
    }

    // 3. Tenta buscar no Google Metadata Server (ambiente Cloud Run / GCP)
    try {
        const cleanAud = audience.endsWith('/') ? audience.slice(0, -1) : audience;
        const metadataUrl = `http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity?audience=${encodeURIComponent(cleanAud)}`;
        const res = await axios.get(metadataUrl, {
            headers: { 'Metadata-Flavor': 'Google' },
            timeout: 1500
        });
        if (res.data) {
            cachedToken = String(res.data).trim();
            tokenExpiry = now + 50 * 60 * 1000; // Cache de 50 minutos
            return cachedToken;
        }
    } catch (_) {
        // Não está no Cloud Run ou metadata indisponível (ex: local)
    }

    return null;
}

class MLflowClient {
    constructor(trackingUri) {
        if (!trackingUri) {
            throw new Error("MLFLOW_TRACKING_URI is required");
        }
        
        this.trackingUri = trackingUri.endsWith('/') ? trackingUri.slice(0, -1) : trackingUri;

        // Configuração do Agente HTTPS para ignorar erros de certificado auto-assinado
        const httpsAgent = new https.Agent({ rejectUnauthorized: false });

        this.client = axios.create({
            baseURL: this.trackingUri,
            headers: {
                'Content-Type': 'application/json'
            },
            httpsAgent: httpsAgent
        });

        // Interceptor para injetar automaticamente o Bearer Token do Google
        this.client.interceptors.request.use(async (config) => {
            const token = await getGoogleIdToken(this.trackingUri);
            if (token) {
                config.headers['Authorization'] = `Bearer ${token}`;
            }
            return config;
        });
    }

    async getExperimentByName(name) {
        try {
            const res = await this.client.get(`/api/2.0/mlflow/experiments/get-by-name`, { params: { experiment_name: name } });
            return res.data.experiment;
        } catch (e) {
            if (e.response && e.response.status === 404) {
                return null;
            }
            throw e;
        }
    }

    async createExperiment(name) {
        const res = await this.client.post(`/api/2.0/mlflow/experiments/create`, { name });
        return res.data.experiment_id;
    }

    async createRun(experimentId, runName) {
        const res = await this.client.post(`/api/2.0/mlflow/runs/create`, {
            experiment_id: experimentId,
            start_time: Date.now(),
            tags: [
                { key: "mlflow.runName", value: runName }
            ]
        });
        return res.data.run.info.run_id;
    }

    async updateRun(runId, status) {
        await this.client.post(`/api/2.0/mlflow/runs/update`, {
            run_id: runId,
            status: status,
            end_time: Date.now()
        });
    }

    async logMetric(runId, key, value) {
        await this.client.post(`/api/2.0/mlflow/runs/log-metric`, {
            run_id: runId,
            key: key,
            value: value,
            timestamp: Date.now()
        });
    }
}

export default MLflowClient;
