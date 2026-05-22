import os
import argparse
from mlflow.server.auth.client import AuthServiceClient

def main():
    parser = argparse.ArgumentParser(description="Ferramenta Administrativa para criar usuários no MLflow.")
    parser.add_argument("username", help="O nome de usuário para o novo cientista de dados.")
    parser.add_argument("password", help="A senha para o novo usuário.")
    parser.add_argument("--admin", action="store_true", help="Se ativado, torna o novo usuário um Administrador.")
    
    args = parser.parse_args()

    tracking_uri = os.environ.get("MLFLOW_TRACKING_URI")
    if not tracking_uri:
        print("❌ ERRO: A variável de ambiente MLFLOW_TRACKING_URI não está definida.")
        print("Exemplo: set MLFLOW_TRACKING_URI=https://mlflow-tracking-server-...")
        return

    # O AuthServiceClient pega as credenciais de ADMIN que devem estar setadas no terminal
    # nas variáveis MLFLOW_TRACKING_USERNAME e MLFLOW_TRACKING_PASSWORD
    print(f"Conectando ao MLflow em {tracking_uri}...")
    try:
        client = AuthServiceClient(tracking_uri)
        
        print(f"Criando usuário '{args.username}'...")
        client.create_user(username=args.username, password=args.password)
        
        if args.admin:
            print(f"Dando privilégios de Administrador para '{args.username}'...")
            client.update_user_admin(username=args.username, is_admin=True)
            
        print(f"✅ Sucesso! O usuário '{args.username}' já pode fazer login na interface web ou rodar scripts!")
        
    except Exception as e:
        print(f"❌ Erro ao criar o usuário. Verifique se o MLFLOW_TRACKING_USERNAME=admin e MLFLOW_TRACKING_PASSWORD=password estão corretos.")
        print(f"Detalhe do erro: {e}")

if __name__ == "__main__":
    main()
