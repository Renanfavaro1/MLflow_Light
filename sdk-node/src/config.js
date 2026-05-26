import MLflowClient from './client.js';

class LightMLflowConfig {
    static experimentId = null;
    static client = null;

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
        } catch (e) {
            console.error("❌ Erro ao configurar MLflow:", e.message);
        }
    }
}

export default LightMLflowConfig;
