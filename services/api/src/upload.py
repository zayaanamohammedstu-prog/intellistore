"""File upload endpoint.

Flow
----
1. Authenticated user POSTs a CSV or Excel file.
2. API saves it under /data/uploads/<job_id>/<original_filename>.
3. API creates an EtlJob record in Postgres with status=pending.
4. API triggers ETL service via HTTP POST /etl/run.
5. API returns job_id + status.

Production TODOs
----------------
- Replace local volume storage with S3 / GCS.
- Replace synchronous HTTP trigger with an async queue (Celery / RQ / SQS).
- Add authentication dependency (verify JWT from request header).
"""
import os
import uuid
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .db import get_db
from .models import EtlJob, User

router = APIRouter(prefix="/uploads", tags=["uploads"])

UPLOADS_DIR = Path(os.getenv("UPLOADS_DIR", "/data/uploads"))
ETL_SERVICE_URL = os.getenv("ETL_SERVICE_URL", "http://etl:8001")
ETL_TRIGGER_TIMEOUT = float(os.getenv("ETL_TRIGGER_TIMEOUT_SECONDS", "10.0"))

ALLOWED_EXTENSIONS = {".csv", ".xls", ".xlsx"}
MAX_FILE_SIZE_BYTES = int(os.getenv("MAX_UPLOAD_SIZE_BYTES", str(50 * 1024 * 1024)))  # 50 MB


class UploadResponse(BaseModel):
    job_id: str
    status: str
    message: str


def _get_demo_user(db: Session) -> User:
    """Return a stub user for demo purposes.

    TODO: Replace with real JWT authentication dependency.
    """
    user = db.query(User).first()
    if user is None:
        user = User(
            google_sub="demo",
            email="demo@example.com",
            name="Demo User",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


@router.post("/", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Accept a CSV/Excel upload, persist it, and trigger ETL processing."""
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported file type '{suffix}'. Allowed: {ALLOWED_EXTENSIONS}",
        )

    # Read file contents (enforces size limit)
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {MAX_FILE_SIZE_BYTES} bytes.",
        )

    job_id = str(uuid.uuid4())
    job_dir = UPLOADS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    stored_path = job_dir / (file.filename or f"upload{suffix}")
    stored_path.write_bytes(contents)

    # Persist ETL job record
    user = _get_demo_user(db)
    job = EtlJob(
        id=uuid.UUID(job_id),
        user_id=user.id,
        original_filename=file.filename or "",
        stored_path=str(stored_path),
        status="pending",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Trigger ETL service asynchronously (fire-and-forget via httpx)
    try:
        async with httpx.AsyncClient(timeout=ETL_TRIGGER_TIMEOUT) as client:
            await client.post(
                f"{ETL_SERVICE_URL}/etl/run",
                json={"job_id": job_id},
            )
    except httpx.RequestError:
        # ETL trigger is best-effort; the job can be retried via polling
        pass

    return UploadResponse(
        job_id=job_id,
        status=job.status,
        message="File received. ETL job queued.",
    )


@router.get("/{job_id}", response_model=UploadResponse)
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """Poll ETL job status by job_id."""
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid job_id format.",
        ) from exc

    job = db.get(EtlJob, job_uuid)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found.",
        )
    return UploadResponse(
        job_id=str(job.id),
        status=job.status,
        message=job.error_message or "",
    )
