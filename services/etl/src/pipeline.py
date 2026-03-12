"""ETL pipeline: ingest → clean → load.

Steps
-----
1. Read uploaded file (CSV or Excel) identified by job_id.
2. Basic cleaning:
   - Strip whitespace from column names and string values.
   - Parse obvious date columns.
   - Drop entirely empty rows.
3. Load into staging_sales_raw table (append).
4. Mark ETL job as completed (or failed on error).

Production TODOs
----------------
- Add schema validation / data-quality checks (Great Expectations or pandera).
- Implement incremental loads / upserts.
- Move to async I/O and a proper queue (Celery / RQ).
- Run fact-table transformations after staging load.
"""
import logging
import uuid
from pathlib import Path

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Columns that will be attempted date-parsing on if they exist.
DATE_COLUMN_HINTS = {"date", "order_date", "sale_date", "transaction_date", "ds"}


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    """Apply minimal cleaning steps to a raw DataFrame."""
    # 1. Normalise column names: strip + lower + replace spaces with underscores
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]

    # 2. Strip leading/trailing whitespace from all string columns
    str_cols = df.select_dtypes(include="object").columns
    df[str_cols] = df[str_cols].apply(lambda col: col.str.strip())

    # 3. Attempt to parse date-like columns
    for col in df.columns:
        if col in DATE_COLUMN_HINTS:
            try:
                df[col] = pd.to_datetime(df[col], infer_datetime_format=True)
            except Exception:  # noqa: BLE001
                pass

    # 4. Drop rows that are entirely empty
    df.dropna(how="all", inplace=True)

    return df


def _ensure_staging_table(session: Session) -> None:
    """Create staging_sales_raw if it does not already exist."""
    session.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS staging_sales_raw (
                id          BIGSERIAL PRIMARY KEY,
                job_id      UUID NOT NULL,
                row_number  INTEGER,
                data        JSONB,
                loaded_at   TIMESTAMPTZ DEFAULT NOW()
            )
            """
        )
    )
    session.commit()


def run_pipeline(job_id: str, stored_path: str, session: Session) -> int:
    """Run the full ETL pipeline for one job.  Returns row count loaded."""
    path = Path(stored_path)
    if not path.exists():
        raise FileNotFoundError(f"Upload file not found: {stored_path}")

    # --- Extract ---
    suffix = path.suffix.lower()
    if suffix == ".csv":
        df = pd.read_csv(path)
    elif suffix in {".xls", ".xlsx"}:
        df = pd.read_excel(path)
    else:
        raise ValueError(f"Unsupported file format: {suffix}")

    # --- Transform ---
    df = _clean(df)
    logger.info("Cleaned dataframe: %d rows, %d columns", len(df), len(df.columns))

    # --- Load ---
    _ensure_staging_table(session)

    job_uuid = uuid.UUID(job_id)

    # Bulk-insert using SQLAlchemy executemany for efficiency.
    import json  # noqa: PLC0415

    def _row_to_json(d: dict) -> str:
        cleaned = {}
        for k, v in d.items():
            if isinstance(v, float) and pd.isna(v):
                cleaned[k] = None
            else:
                cleaned[k] = str(v) if not isinstance(v, (int, float, bool, type(None))) else v
        return json.dumps(cleaned)

    params = [
        {
            "job_id": str(job_uuid),
            "row_number": int(idx),
            "data": _row_to_json(row),
        }
        for idx, row in df.reset_index(drop=True).to_dict(orient="index").items()
    ]

    with session.bind.connect() as conn:
        conn.execute(
            text(
                "INSERT INTO staging_sales_raw (job_id, row_number, data) "
                "VALUES (:job_id, :row_number, :data::jsonb)"
            ),
            params,
        )
        conn.commit()

    return len(df)
