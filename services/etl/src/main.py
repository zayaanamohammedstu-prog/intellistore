"""ETL service – FastAPI application."""
import logging

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from .db import SessionLocal, engine, get_db
from .pipeline import run_pipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="IntelliStore ETL Service",
    description="Ingests uploaded sales files and loads them into the data warehouse.",
    version="0.1.0",
)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@app.get("/health", tags=["ops"])
def health():
    """Liveness probe."""
    return {"status": "ok", "service": "etl"}


# ---------------------------------------------------------------------------
# ETL run endpoint
# ---------------------------------------------------------------------------
class EtlRunRequest(BaseModel):
    job_id: str


class EtlRunResponse(BaseModel):
    job_id: str
    status: str
    rows_loaded: int | None = None
    error: str | None = None


@app.post("/etl/run", response_model=EtlRunResponse)
def etl_run(body: EtlRunRequest, db: Session = Depends(get_db)):
    """Trigger the ETL pipeline for a specific job_id.

    Called by the API service after a file is uploaded.
    """
    job_id = body.job_id

    # Fetch job record from DB (assumes shared Postgres instance)
    row = db.execute(
        text("SELECT stored_path, status FROM etl_jobs WHERE id = :id"),
        {"id": job_id},
    ).fetchone()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ETL job {job_id} not found.",
        )

    if row.status not in ("pending", "failed"):
        return EtlRunResponse(job_id=job_id, status=row.status)

    # Mark as running
    db.execute(
        text("UPDATE etl_jobs SET status = 'running', updated_at = NOW() WHERE id = :id"),
        {"id": job_id},
    )
    db.commit()

    try:
        rows_loaded = run_pipeline(job_id, row.stored_path, db)
        db.execute(
            text(
                "UPDATE etl_jobs SET status = 'completed', updated_at = NOW() WHERE id = :id"
            ),
            {"id": job_id},
        )
        db.commit()
        logger.info("Job %s completed: %d rows loaded.", job_id, rows_loaded)
        return EtlRunResponse(job_id=job_id, status="completed", rows_loaded=rows_loaded)
    except Exception as exc:  # noqa: BLE001
        db.execute(
            text(
                "UPDATE etl_jobs SET status = 'failed', error_message = :err, updated_at = NOW() "
                "WHERE id = :id"
            ),
            {"id": job_id, "err": str(exc)},
        )
        db.commit()
        logger.exception("Job %s failed.", job_id)
        return EtlRunResponse(job_id=job_id, status="failed", error=str(exc))
