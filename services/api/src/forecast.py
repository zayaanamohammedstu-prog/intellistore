"""Forecast endpoint.

Loads a trained .pkl model exported from Google Colab and exposes a
prediction endpoint.

Model integration instructions
-------------------------------
1. Train your model in Google Colab (Prophet, sklearn pipeline, etc.).
2. Export it:
       import pickle
       with open("model.pkl", "wb") as f:
           pickle.dump(model, f)
3. Place the file at:  services/api/models/forecast/model.pkl
4. The model.pkl path inside the container is /app/models/forecast/model.pkl
   (mapped via the Dockerfile COPY instruction).

The model must expose a `.predict()` method that accepts a pandas DataFrame
with at least the columns listed in FEATURE_COLUMNS below.  Adjust these to
match your actual trained model.

Production TODOs
----------------
- Validate input against a feature schema / JSON Schema.
- Cache predictions in Redis or Postgres.
- Version-stamp the loaded model (metadata.json).
- Replace mocked input with real data fetched from the warehouse.
"""
import os
import pickle
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

router = APIRouter(prefix="/forecast", tags=["forecast"])

MODEL_PATH = Path(
    os.getenv("FORECAST_MODEL_PATH", "/app/models/forecast/model.pkl")
)

# Feature columns expected by the trained model.
# TODO: Update to match your exported model's feature set.
FEATURE_COLUMNS: list[str] = ["ds", "store_id", "product_id"]

_model_cache: dict[str, Any] = {}


def _load_model() -> Any:
    """Load the pickled model lazily and cache it in memory.

    Security note: Only load model files from trusted sources.  The pickle
    format can execute arbitrary Python code during deserialization.  Never
    load a model file supplied by an end-user or downloaded from an
    untrusted location.  For production, consider safer serialisation
    formats such as ONNX or joblib with a restricted unpickler.
    """
    if "model" not in _model_cache:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Model file not found at {MODEL_PATH}. "
                "See services/api/models/forecast/README.md for instructions."
            )
        with MODEL_PATH.open("rb") as fh:
            _model_cache["model"] = pickle.load(fh)  # noqa: S301
    return _model_cache["model"]


class ForecastRequest(BaseModel):
    store_id: str
    product_id: str
    horizon_days: int = 30


class ForecastResponse(BaseModel):
    store_id: str
    product_id: str
    horizon_days: int
    predictions: list[dict]


@router.post("/run", response_model=ForecastResponse)
def run_forecast(body: ForecastRequest):
    """Load the trained model and return a sales forecast.

    If no real model is present a mocked response is returned so the rest of
    the stack can be exercised end-to-end during development.
    """
    try:
        model = _load_model()
        # Build a minimal input DataFrame matching the model's expected format.
        # TODO: Replace with real future dates + feature engineering.
        future_dates = pd.date_range(
            start=pd.Timestamp.today(), periods=body.horizon_days, freq="D"
        )
        input_df = pd.DataFrame(
            {
                "ds": future_dates,
                "store_id": body.store_id,
                "product_id": body.product_id,
            }
        )
        raw = model.predict(input_df)
        # Normalise to a JSON-serialisable list of records.
        if isinstance(raw, pd.DataFrame):
            predictions = raw.to_dict(orient="records")
        else:
            predictions = [{"yhat": float(v)} for v in raw]
    except FileNotFoundError:
        # No model deployed yet — return mocked predictions for development.
        predictions = [
            {"ds": str(pd.Timestamp.today() + pd.Timedelta(days=i)), "yhat": 100.0}
            for i in range(body.horizon_days)
        ]
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Forecast error: {exc}",
        ) from exc

    return ForecastResponse(
        store_id=body.store_id,
        product_id=body.product_id,
        horizon_days=body.horizon_days,
        predictions=predictions,
    )
