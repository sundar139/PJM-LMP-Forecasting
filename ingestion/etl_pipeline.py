from pathlib import Path
import argparse

import pandas as pd

from ingestion.config import RAW_DIR, PROCESSED_DIR, ensure_local_dirs, settings


def process_raw_file(raw_path: Path) -> Path:
    ensure_local_dirs()
    print(f"Processing {raw_path}")

    df = pd.read_parquet(raw_path)

    ts_candidates = [
        "interval_start_utc",
        "interval_start",
        "Interval Start",
        "Time",
        "Forecast Time",
    ]
    ts_col = next((c for c in ts_candidates if c in df.columns), None)
    if ts_col is None:
        raise ValueError("Could not find timestamp column in raw data")
    ts = pd.to_datetime(df[ts_col], errors="coerce")
    if hasattr(ts, "dt") and ts.dt.tz is not None:
        ts = ts.dt.tz_convert("UTC")
    else:
        ts = pd.to_datetime(ts, utc=True)
    df["interval_start_utc"] = ts

    col_map = {
        "Location": "node_id",
        "Location Name": "node_name",
        "LMP": "total_lmp",
        "Congestion": "congestion_price",
        "Loss": "marginal_loss_price",
        "Load": "load",
        "Load Forecast": "load_forecast",
    }
    present_map = {k: v for k, v in col_map.items() if k in df.columns}
    df = df.rename(columns=present_map)

    # Example: keep subset of columns
    keep_cols = [
        "interval_start_utc",
        "node_id",
        "node_name",
        "total_lmp",
        "congestion_price",
        "marginal_loss_price",
        "load",
        "load_forecast",
        "source",
    ]
    for col in keep_cols:
        if col not in df.columns:
            df[col] = None

    df = df[keep_cols]

    # Negative prices allowed, but clip insane outliers
    df["total_lmp"] = pd.to_numeric(df["total_lmp"], errors="coerce")
    df["total_lmp"] = df["total_lmp"].clip(lower=-200, upper=5000)

    out_name = raw_path.name.replace("raw", "processed")
    out_path = PROCESSED_DIR / out_name
    df.to_parquet(out_path, index=False)
    print(f"Wrote processed data to {out_path}")

    if settings.use_s3:
        try:
            import boto3
        except Exception:
            raise SystemExit("USE_S3=1 requires boto3 installed")
        if not settings.s3_bucket_processed:
            raise SystemExit("S3_BUCKET_PROCESSED must be set when USE_S3=1")
        s3 = boto3.client("s3", region_name=settings.aws_region)
        key = f"processed/{out_path.name}"
        s3.upload_file(str(out_path), settings.s3_bucket_processed, key)
        print(f"Uploaded {out_path} to s3://{settings.s3_bucket_processed}/{key}")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-path", type=str, required=True)
    args = parser.parse_args()

    raw_path = Path(args.raw_path)
    if not raw_path.exists():
        raise SystemExit(f"{raw_path} does not exist")

    process_raw_file(raw_path)


if __name__ == "__main__":
    main()
