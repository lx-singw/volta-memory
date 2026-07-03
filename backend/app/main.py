"""FastAPI entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_chat import router as chat_router
from app.api.routes_eval import router as eval_router
from app.api.routes_memory_debug import router as memory_router
from app.config import get_settings
from app.db import check_database, close_pool, get_pool

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
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(memory_router)
app.include_router(eval_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "database": check_database()}
