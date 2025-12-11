import argparse
from pathlib import Path
from typing import List

import mlflow
import mlflow.xgboost
from mlflow.models import infer_signature
import numpy as np
import pandas as pd
from xgboost import XGBRegressor

from ingestion.config import PROCESSED_DIR, settings
from feature_repo.feature_definitions import build_features


TARGET_COLUMN = "total_lmp"


def load_processed_data(limit_files: int | None = None) -> pd.DataFrame:
    files = sorted(PROCESSED_DIR.glob("pjm_processed_*.parquet"))
    if not files:
        raise FileNotFoundError("No processed files found in data/processed")

    if limit_files:
        files = files[-limit_files:]

    dfs = [pd.read_parquet(f) for f in files]
    df = pd.concat(dfs, ignore_index=True)
    df["interval_start_utc"] = pd.to_datetime(df["interval_start_utc"], utc=True)
    return df


def train_test_split_time(df: pd.DataFrame, test_ratio: float = 0.2):
    df = df.sort_values("interval_start_utc")
    cutoff = int(len(df) * (1 - test_ratio))
    train = df.iloc[:cutoff]
    test = df.iloc[cutoff:]
    return train, test


def get_feature_columns(df: pd.DataFrame) -> List[str]:
    exclude = [
        "interval_start_utc",
        "node_id",
        "node_name",
        "source",
        TARGET_COLUMN,
    ]
    return [c for c in df.columns if c not in exclude]


def train_model(test_run: bool = False, limit_files: int | None = None) -> None:
    mlflow.set_tracking_uri("file:./mlruns")
    mlflow.set_experiment("pjm_lmp_xgboost")

    with mlflow.start_run():
        df = load_processed_data(limit_files=limit_files)
        df = df[df["source"] == "rt_lmp"]
        df = build_features(df)
        if df.empty or len(df) < 100:
            raise SystemExit("Not enough rows after feature engineering. Increase data window.")

        features = get_feature_columns(df)
        X = df[features].apply(pd.to_numeric, errors="coerce")
        y = pd.to_numeric(df[TARGET_COLUMN], errors="coerce")

        train_df, test_df = train_test_split_time(df)
        X_train = train_df[features].apply(pd.to_numeric, errors="coerce")
        y_train = pd.to_numeric(train_df[TARGET_COLUMN], errors="coerce")
        X_test = test_df[features].apply(pd.to_numeric, errors="coerce")
        y_test = pd.to_numeric(test_df[TARGET_COLUMN], errors="coerce")
        if X_train.isna().any().any() or y_train.isna().any() or X_test.isna().any().any() or y_test.isna().any():
            X_train = X_train.fillna(0.0)
            X_test = X_test.fillna(0.0)
            y_train = y_train.fillna(method="ffill").fillna(method="bfill")
            y_test = y_test.fillna(method="ffill").fillna(method="bfill")

        X_train = X_train.astype(np.float64)
        X_test = X_test.astype(np.float64)
        y_train = y_train.astype(np.float64)
        y_test = y_test.astype(np.float64)

        params = {
            "learning_rate": 0.05,
            "max_depth": 6,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "n_estimators": 500,
            "objective": "reg:squarederror",
            "tree_method": "hist",
        }

        if test_run:
            params["n_estimators"] = 50

        mlflow.log_params(params)

        model = XGBRegressor(**params)
        model.fit(
            X_train,
            y_train,
            eval_set=[(X_test, y_test)],
            verbose=False,
        )

        y_pred = model.predict(X_test)
        rmse = float(np.sqrt(np.mean((y_pred - y_test) ** 2)))
        mae = float(np.mean(np.abs(y_pred - y_test)))

        mlflow.log_metric("rmse", rmse)
        mlflow.log_metric("mae", mae)

        # Placeholder Sharpe ratio: use simple return-like metric
        returns = y_test.values - y_pred
        if returns.std() > 0:
            sharpe = float(returns.mean() / returns.std())
            mlflow.log_metric("sharpe_like", sharpe)

        signature = infer_signature(X_test, model.predict(X_test))
        mlflow.xgboost.log_model(
            xgb_model=model,
            artifact_path="model",
            registered_model_name="pjm_lmp_xgb_model",
            signature=signature,
            input_example=X_test.head(1).astype(np.float64),
        )

        out_path = Path("data/models/xgb_rt_lmp.json")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        model.save_model(out_path)
        print(f"Model saved to {out_path}")
        print(f"RMSE={rmse:.3f}, MAE={mae:.3f}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--test-run",
        action="store_true",
        help="Train quickly on a small subset",
    )
    args = parser.parse_args()

    if args.test_run:
        train_model(test_run=True, limit_files=1)
    else:
        train_model(test_run=False, limit_files=None)


if __name__ == "__main__":
    main()
