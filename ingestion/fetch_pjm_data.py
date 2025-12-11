import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
from gridstatus import PJM

from ingestion.config import RAW_DIR, ensure_local_dirs, settings


def _parse_date(date_str: str) -> datetime:
    return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def fetch_lmp_and_load(start_date: datetime, end_date: datetime) -> None:
    ensure_local_dirs()
    client = PJM()

    print(f"Fetching data from {start_date} to {end_date} (UTC)")

    # Real-time LMP (5-min)
    rt = client.get_lmp(
        market=settings.pjm_market_rt,
        start=start_date,
        end=end_date,
    )
    rt["source"] = "rt_lmp"

    # Day-ahead LMP (hourly)
    da = client.get_lmp(
        market=settings.pjm_market_da,
        start=start_date,
        end=end_date,
    )
    da["source"] = "da_lmp"

    # Load forecast + metered load
    load_forecast = client.get_load_forecast(date="today")
    load_forecast["source"] = "load_forecast"

    load_metered = client.get_load(date=start_date, end=end_date)
    load_metered["source"] = "load_metered"

    df = pd.concat([rt, da, load_forecast, load_metered], ignore_index=True)

    out_path = RAW_DIR / f"pjm_raw_{start_date:%Y%m%d}_{end_date:%Y%m%d}.parquet"
    df.to_parquet(out_path, index=False)
    print(f"Wrote raw data to {out_path}")

    if settings.use_s3:
        try:
            import boto3
        except Exception as e:
            raise SystemExit("USE_S3=1 requires boto3 installed")
        if not settings.s3_bucket_raw:
            raise SystemExit("S3_BUCKET_RAW must be set when USE_S3=1")
        s3 = boto3.client("s3", region_name=settings.aws_region)
        key = f"raw/{out_path.name}"
        s3.upload_file(str(out_path), settings.s3_bucket_raw, key)
        print(f"Uploaded {out_path} to s3://{settings.s3_bucket_raw}/{key}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-date", type=str, help="YYYY-MM-DD")
    parser.add_argument("--end-date", type=str, help="YYYY-MM-DD")
    parser.add_argument(
        "--test-run",
        action="store_true",
        help="Use last 1 day of data for quick testing",
    )
    args = parser.parse_args()

    if args.test_run:
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=1)
    else:
        if not args.start_date or not args.end_date:
            raise SystemExit(
                "Either provide --start-date and --end-date or use --test-run"
            )
        start = _parse_date(args.start_date)
        end = _parse_date(args.end_date)

    fetch_lmp_and_load(start, end)


if __name__ == "__main__":
    main()
