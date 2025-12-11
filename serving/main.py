from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from ingestion.config import PROCESSED_DIR
from feature_repo.feature_definitions import build_features
from serving.model_loader import get_model


app = FastAPI(title="PJM LMP Forecasting API")


class PredictionRequest(BaseModel):
    timestamp_utc: datetime | None = None


class PredictionResponse(BaseModel):
    timestamp_utc: datetime
    predicted_lmp: float
    features_used: List[str]


def load_latest_features() -> pd.DataFrame:
    files = sorted(PROCESSED_DIR.glob("pjm_processed_*.parquet"))
    if not files:
        raise RuntimeError("No processed files found for serving.")
    df = pd.read_parquet(files[-1])
    df["interval_start_utc"] = pd.to_datetime(df["interval_start_utc"], utc=True)
    df = df[df["source"] == "rt_lmp"]

    df_feat = build_features(df)
    return df_feat


@app.get("/health")
def health():
    return {"status": "ok"}


 


@app.post("/predict", response_model=PredictionResponse)
def predict(req: PredictionRequest):
    model = get_model()
    df = load_latest_features()

    if req.timestamp_utc:
        ts = req.timestamp_utc.astimezone(timezone.utc)
        ts = ts.replace(second=0, microsecond=0)
        ts = ts - timedelta(minutes=ts.minute % 5)
        row = df[df["interval_start_utc"] == ts]
        if row.empty:
            nearest_idx = (df["interval_start_utc"] - ts).abs().idxmin()
            nearest_row = df.loc[[nearest_idx]]
            if (nearest_row["interval_start_utc"].iloc[0] - ts).abs() <= timedelta(minutes=10):
                row = nearest_row
            else:
                row = df.sort_values("interval_start_utc").tail(1)
    else:
        row = df.sort_values("interval_start_utc").tail(1)

    exclude = [
        "interval_start_utc",
        "node_id",
        "node_name",
        "source",
        "total_lmp",
    ]
    features = [c for c in row.columns if c not in exclude]
    X = row[features].apply(pd.to_numeric, errors="coerce").fillna(0.0)

    y_pred = model.predict(X)[0]
    ts_out = row["interval_start_utc"].iloc[0].to_pydatetime()

    return PredictionResponse(
        timestamp_utc=ts_out,
        predicted_lmp=float(y_pred),
        features_used=features,
    )
