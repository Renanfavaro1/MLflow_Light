from light_mlflow import LightMLflowConfig
from light_mlflow.decorators import train_model
from sklearn.ensemble import RandomForestClassifier
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split

# 1. Configura a conexão (usa MLFLOW_TRACKING_URI se não passar a URI)
LightMLflowConfig.setup(experiment_name="Previsao_de_Fraude")

# 2. O decorator ativa o autolog() do MLflow automaticamente
@train_model(run_name="RandomForest_Baseline")
def executar_treinamento():
    X, y = load_iris(return_X_y=True)
    X_train, X_test, y_train, y_test = train_test_split(X, y)
    
    model = RandomForestClassifier(n_estimators=50, max_depth=5)
    
    # Neste momento, o MLflow captura os hiperparâmetros e salva o modelo no GCP
    model.fit(X_train, y_train)
    
    score = model.score(X_test, y_test)
    print(f"Treinamento concluído. Acurácia: {score}")
    
    return model

if __name__ == "__main__":
    executar_treinamento()
