"""FastAPI entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from app.api.routes_chat import router as chat_router
from app.api.routes_eval import router as eval_router
from app.api.routes_memory_debug import router as memory_router
from app.api.routes_v1 import router as v1_router
from app.config import get_settings
from app.db import check_database, close_pool, get_pool
from app.auth import require_admin

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
    logger.info("Starting Volta Memory (%s)", settings.app_env)
    if settings.log_redact_api_keys:
        logger.info("Loaded config: %s", settings.redacted_repr())
    get_pool()
    yield
    close_pool()


app = FastAPI(title="Volta Memory API", version="0.1.0", lifespan=lifespan)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-CSRF-Token", "Idempotency-Key", "X-Admin-Key"],
)


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    if request.url.path.startswith(("/v1", "/sessions", "/entities", "/eval")):
        response.headers.setdefault("Cache-Control", "no-store")
    return response

# Legacy diagnostic/control routes remain available to locally authorised
# operators, but must not advertise public reset/reseed/evaluation surfaces to
# judges or API consumers in production. The product API stays documented.
_legacy_routes_visible = settings.app_env != "production"
app.include_router(chat_router, include_in_schema=_legacy_routes_visible)
app.include_router(memory_router, include_in_schema=_legacy_routes_visible)
app.include_router(eval_router, include_in_schema=_legacy_routes_visible)
app.include_router(v1_router)


@app.get("/health")
def health() -> dict:
    """Fast liveness check that does not spend a database connection."""
    return {"status": "ok"}


@app.get("/ready")
def readiness(request: Request, response: Response) -> dict:
    # Liveness is deliberately public; database/readiness state is operational
    # information and requires explicit admin authority in production.
    if settings.app_env == "production":
        require_admin(request)
    database = check_database()
    if not database:
        response.status_code = 503
    return {"status": "ok" if database else "degraded", "database": database}


# Serve static frontend files if bundled
static_dir = Path(__file__).resolve().parent / "static"
# Production uses OSS/CDN for the static Next.js export. Local development may
# still serve the bundle for one-command testing, while production requires an
# explicit emergency opt-in to avoid shipping a stale frontend from Function Compute.
if static_dir.exists() and (settings.app_env != "production" or settings.serve_bundled_static):
    app.mount("/_next", StaticFiles(directory=str(static_dir / "_next")), name="next_static")

    def _serve_static_path(path: str) -> FileResponse:
        """Resolve Next's static-export directory indexes without path escape."""
        static_root = static_dir.resolve()
        candidate = (static_root / path.lstrip("/")).resolve()
        if candidate != static_root and static_root not in candidate.parents:
            return FileResponse(str(static_root / "index.html"))
        if candidate.is_dir():
            candidate = candidate / "index.html"
        if candidate.is_file():
            return FileResponse(str(candidate))
        return FileResponse(str(static_root / "index.html"))

    @app.get("/")
    def serve_index():
        return _serve_static_path("")

    @app.get("/memory")
    def serve_memory():
        return _serve_static_path("memory")

    @app.get("/{file_name:path}")
    def serve_file(file_name: str):
        return _serve_static_path(file_name)
