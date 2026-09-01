"""
Light Auth Middleware for MLflow.

Pure ASGI middleware that wraps the MLflow app with authentication.
- Bearer tokens: agents/services pass through (already authenticated via Cloud Run IAM)
- Basic Auth: humans must provide user/password to access the MLflow UI
- Health endpoints: always public (for Cloud Run probes)

Usage: mlflow server --app-name auth_wrapper:app
"""
import os
import base64


BASIC_AUTH_USER = os.environ.get("BASIC_AUTH_USER", "light")
BASIC_AUTH_PASS = os.environ.get("BASIC_AUTH_PASS", "Light@2026")

# Paths that skip authentication (Cloud Run health probes)
PUBLIC_PATHS = frozenset({"/health", "/version"})


async def _send_401(send):
    """Send a 401 response that triggers the browser's native login dialog."""
    body = b"Acesso restrito - Area Light MLflow"
    await send({
        "type": "http.response.start",
        "status": 401,
        "headers": [
            [b"content-type", b"text/plain; charset=utf-8"],
            [b"content-length", str(len(body)).encode()],
            [b"www-authenticate", b'Basic realm="Acesso a Area Light MLflow"'],
        ],
    })
    await send({
        "type": "http.response.body",
        "body": body,
    })


def _is_authorized(headers_list):
    """Check authorization from raw ASGI headers. Returns True if authorized."""
    auth_value = b""
    for name, value in headers_list:
        if name == b"authorization":
            auth_value = value
            break

    if not auth_value:
        return False

    auth_str = auth_value.decode("latin-1")

    # Bearer tokens -> agents/services authenticated at Cloud Run IAM layer
    if auth_str.startswith("Bearer "):
        return True

    # Basic Auth -> human users accessing the MLflow UI via browser
    if auth_str.startswith("Basic "):
        try:
            encoded = auth_str.split(" ", 1)[1]
            decoded = base64.b64decode(encoded).decode("utf-8")
            user, pwd = decoded.split(":", 1)
            return user == BASIC_AUTH_USER and pwd == BASIC_AUTH_PASS
        except Exception:
            return False

    return False


class LightAuthMiddleware:
    """Pure ASGI middleware -- zero external dependencies."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        # Health probes pass through
        if scope.get("path", "") in PUBLIC_PATHS:
            return await self.app(scope, receive, send)

        # Check credentials
        if not _is_authorized(scope.get("headers", [])):
            return await _send_401(send)

        return await self.app(scope, receive, send)


# ---------------------------------------------------------------------------
# Import the MLflow ASGI app.
#
# When this module is loaded by Gunicorn (via `mlflow server --app-name
# auth_wrapper:app`), the `mlflow server` CLI has *already* set the internal
# env vars (_MLFLOW_SERVER_FILE_STORE, _MLFLOW_SERVER_ARTIFACT_ROOT, etc.).
# So the MLflow app initializes correctly with the right backend store and
# artifact root -- no manual env-var mapping needed.
# ---------------------------------------------------------------------------
from mlflow.server import app as _mlflow_app  # noqa: E402

# Wrap the MLflow app with our auth layer.
# This `app` attribute is what Gunicorn/Uvicorn will serve.
app = LightAuthMiddleware(_mlflow_app)
