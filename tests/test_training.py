import pandas as pd
from pathlib import Path

from training.train_xgb import (
    get_feature_columns,
    train_model,
)
from ingestion.config import PROCESSED_DIR


def test_feature_columns_exclusion():
    df = pd.DataFrame(
        {
            "interval_start_utc": pd.date_range("2025-01-01", periods=10, tz="UTC"),
            "node_id": [51217] * 10,
            "node_name": ["X"] * 10,
            "source": ["rt_lmp"] * 10,
            "total_lmp": range(10),
            "f1": range(10),
            "f2": range(10),
        }
    )
    features = get_feature_columns(df)
    assert "total_lmp" not in features
    assert "interval_start_utc" not in features
    assert "f1" in features


def test_training_smoke():
    processed = list(PROCESSED_DIR.glob("pjm_processed_*.parquet"))
    if not processed:
        return

    train_model(test_run=True, limit_files=1)
    model_path = Path("data/models/xgb_rt_lmp.json")
    assert model_path.exists()
