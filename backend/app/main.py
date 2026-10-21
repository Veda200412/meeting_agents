"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.db.database import init_db
from app.api.routes import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    settings = get_settings()
    warnings = settings.validate_startup()
    for w in warnings:
        logger.warning("CONFIG: %s", w)

    init_db()
    logger.info("Database initialized")
    logger.info("LLM Provider: %s, Model: %s", settings.LLM_PROVIDER, settings.LLM_MODEL)
    logger.info("Demo faults: %s", "enabled" if settings.ENABLE_DEMO_FAULTS else "disabled")

    yield

    logger.info("Application shutting down")


app = FastAPI(
    title="AI Operations Coordinator",
    description="Three LLM-powered agents collaborating to produce reviewed action plans.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN, "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
