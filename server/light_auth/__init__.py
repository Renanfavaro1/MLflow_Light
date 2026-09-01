import os
import base64
from flask import request, Response

BASIC_AUTH_USER = os.environ.get("BASIC_AUTH_USER", "light")
BASIC_AUTH_PASS = os.environ.get("BASIC_AUTH_PASS", "Light@2026")

def create_app(app=None):
    """
    MLflow App Plugin Factory.
    Attaches authentication to the native MLflow Flask application.
    """
    if app is None:
        from mlflow.server import app as mlflow_app
        app = mlflow_app

    @app.before_request
    def check_light_auth():
        # Permite healthcheck do Cloud Run sem autenticação
        if request.path in ("/health", "/version"):
            return None

        auth_header = request.headers.get("Authorization", "")

        # 1. Agentes e Serviços que usam Bearer token (passam direto)
        if auth_header.startswith("Bearer "):
            return None

        # 2. Usuários humanos no navegador usando Login Light (Basic Auth)
        if auth_header.startswith("Basic "):
            try:
                encoded = auth_header.split(" ", 1)[1]
                decoded = base64.b64decode(encoded).decode("utf-8")
                user, pwd = decoded.split(":", 1)
                if user == BASIC_AUTH_USER and pwd == BASIC_AUTH_PASS:
                    return None
            except Exception:
                pass

        # 3. Não autenticado -> Dispara o popup nativo de login no navegador
        return Response(
            "Acesso restrito - Area Light MLflow",
            401,
            {"WWW-Authenticate": 'Basic realm="Acesso a Area Light MLflow"'}
        )

    return app
