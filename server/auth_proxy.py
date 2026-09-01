from flask import Flask, request, Response
import requests
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import base64
import os

app = Flask(__name__)
MLFLOW_URL = "http://127.0.0.1:5001"

# Credenciais da Area Light
ADMIN_USER = os.environ.get("BASIC_AUTH_USER", "light")
ADMIN_PASS = os.environ.get("BASIC_AUTH_PASS", "Light@2026")
AUDIENCE = os.environ.get("AUTH_AUDIENCE")

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'])
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'])
def proxy(path):
    auth_header = request.headers.get("Authorization")
    authorized = False
    
    # 1. Verifica autenticacao
    if auth_header:
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                # Verifica o Token ID do Google (usado pelos agentes)
                id_token.verify_oauth2_token(token, google_requests.Request(), audience=AUDIENCE if AUDIENCE else None)
                authorized = True
            except Exception as e:
                print(f"Token error: {e}")
        elif auth_header.startswith("Basic "):
            try:
                # Verifica usuario e senha (usado pela tela do navegador)
                encoded = auth_header.split(" ")[1]
                decoded = base64.b64decode(encoded).decode("utf-8")
                user, pwd = decoded.split(":", 1)
                if user == ADMIN_USER and pwd == ADMIN_PASS:
                    authorized = True
            except Exception as e:
                print(f"Basic Auth error: {e}")

    # 2. Se nao estiver autorizado e nao for o healthcheck, bloqueia com 401
    if not authorized and path != "health":
        return Response('Unauthorized', 401, {'WWW-Authenticate': 'Basic realm="Acesso a Area Light MLflow"'})

    # 3. Encaminha a requisicao para o MLflow original (rodando na porta 5001)
    url = f"{MLFLOW_URL}/{path}"
    if request.query_string:
        url = f"{url}?{request.query_string.decode('utf-8')}"
        
    # Remove o header Host para o requests gerar um novo apropriado para o localhost
    headers = {key: value for (key, value) in request.headers if key.lower() != 'host'}
    
    try:
        resp = requests.request(
            method=request.method,
            url=url,
            headers=headers,
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False,
            stream=True
        )
        
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        resp_headers = [(name, value) for (name, value) in resp.raw.headers.items()
                   if name.lower() not in excluded_headers]

        return Response(resp.iter_content(chunk_size=10*1024), resp.status_code, resp_headers)
    except Exception as e:
        return Response(f"Proxy error: {e}", 502)
