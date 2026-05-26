import axios from 'axios';
import https from 'https';

class MLflowClient {
    constructor(trackingUri) {
        if (!trackingUri) {
            throw new Error("MLFLOW_TRACKING_URI is required");
        }
        
        // Configuração do Agente HTTPS para ignorar erros de certificado auto-assinado
        // (Útil para contornar bloqueios de proxy corporativo como o da Light)
        const httpsAgent = new https.Agent({ rejectUnauthorized: false });

        this.client = axios.create({
            baseURL: trackingUri.endsWith('/') ? trackingUri.slice(0, -1) : trackingUri,
            headers: {
                'Content-Type': 'application/json'
            },
            httpsAgent: httpsAgent
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
