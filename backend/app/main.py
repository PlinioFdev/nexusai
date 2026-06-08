from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import settings
from app.api.v1 import api_router

# Apenas POST /widget/chat é público — os demais endpoints do widget requerem JWT
WIDGET_PUBLIC_PATHS = {"/api/v1/widget/chat"}

_dashboard_origins = {str(o).rstrip("/") for o in settings.BACKEND_CORS_ORIGINS}


class SmartCORSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        origin = request.headers.get("origin", "")
        is_public_widget = request.url.path in WIDGET_PUBLIC_PATHS

        # Preflight OPTIONS — responde imediatamente sem chamar o handler
        if request.method == "OPTIONS":
            response = Response(status_code=204)
        else:
            response = await call_next(request)

        if is_public_widget:
            # Endpoint público do widget: qualquer origem, sem credentials
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        elif origin in _dashboard_origins:
            # Dashboard e endpoints autenticados do widget: origem conhecida, com credentials
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "*"
            response.headers["Access-Control-Allow-Headers"] = "*"
            response.headers["Vary"] = "Origin"

        return response


app = FastAPI(
    title="NexusAI API",
    version="0.1.0",
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
)

app.add_middleware(SmartCORSMiddleware)
app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
def health_check() -> dict:
    return {"status": "ok", "version": "0.1.0"}
