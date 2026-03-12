"""IntelliStore API – main application entry point."""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import router as auth_router
from .db import Base, engine
from .forecast import router as forecast_router
from .upload import router as upload_router


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create all tables on startup.

    TODO: Replace with Alembic migrations in production.
    """
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="IntelliStore API",
    description="ShopIntel / IntelliStore backend – ETL orchestration, auth, and forecasting.",
    version="0.1.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(auth_router)
app.include_router(upload_router)
app.include_router(forecast_router)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@app.get("/health", tags=["ops"])
def health():
    """Liveness probe."""
    return {"status": "ok", "service": "api"}
