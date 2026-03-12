# Forecast Model Placeholder

Place your trained model artifact here before running the API service.

## How to export from Google Colab

```python
import pickle

# After training your model (e.g. Prophet, sklearn Pipeline, etc.)
with open("model.pkl", "wb") as f:
    pickle.dump(model, f)
```

Then copy the file into this directory:

```
services/api/models/forecast/model.pkl
```

## Expected interface

The model object must expose a `.predict(df)` method that:

- Accepts a `pandas.DataFrame` with at minimum the columns:
  `ds` (datetime), `store_id` (str), `product_id` (str)
- Returns either a `pandas.DataFrame` (with a `yhat` column) **or** a
  1-D array-like of float predictions.

## Gitignore note

`*.pkl`, `*.joblib`, `*.pt`, and `*.h5` files in this directory are excluded
from git (see `.gitignore` at the repo root) to avoid committing large binary
blobs.  Store models in object storage (S3 / GCS) for production deployments.
