import os
import base64
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

BASIC_AUTH_USER = os.environ.get("BASIC_AUTH_USER", "light")
BASIC_AUTH_PASS = os.environ.get("BASIC_AUTH_PASS", "Light@2026")

class LightAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # 1. Healthcheck probes do Cloud Run
        if request.url.path in ("/health", "/version"):
            return await call_next(request)

        auth_header = request.headers.get("authorization", "")

        # 2. Agentes de IA com Bearer Token (passam direto)
        if auth_header.startswith("Bearer "):
            return await call_next(request)

        # 3. Usuários no Navegador com Basic Auth (Login Light)
        if auth_header.startswith("Basic "):
            try:
                encoded = auth_header.split(" ", 1)[1]
                decoded = base64.b64decode(encoded).decode("utf-8")
                user, pwd = decoded.split(":", 1)
                if user == BASIC_AUTH_USER and pwd == BASIC_AUTH_PASS:
                    return await call_next(request)
            except Exception:
                pass

        # 4. Não autorizado -> Exibe tela/popup de login no navegador
        return Response(
            content="Acesso restrito - Area Light MLflow",
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="Acesso a Area Light MLflow"'}
        )

def create_app(app=None):
    """
    MLflow App Plugin Factory.
    Envolve o aplicativo FastAPI/ASGI do MLflow com o middleware de autenticação.
    """
    if app is None:
        try:
            from mlflow.server.fastapi_app import app as mlflow_app
        except ImportError:
            from mlflow.server import app as mlflow_app
        app = mlflow_app

    if hasattr(app, "add_middleware"):
        app.add_middleware(LightAuthMiddleware)
        return app
    else:
        from starlette.middleware.wsgi import WSGIMiddleware
        from fastapi import FastAPI
        fastapi_wrapper = FastAPI()
        fastapi_wrapper.add_middleware(LightAuthMiddleware)
        fastapi_wrapper.mount("/", WSGIMiddleware(app))
        return fastapi_wrapper
