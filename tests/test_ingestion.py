from pathlib import Path

from ingestion.config import RAW_DIR, PROCESSED_DIR
from ingestion.etl_pipeline import process_raw_file


def test_process_raw_file_smoke():
    raw_files = list(RAW_DIR.glob("pjm_raw_*.parquet"))
    if not raw_files:
        # In CI you would fail; locally you can skip.
        return

    out_path = process_raw_file(raw_files[-1])
    assert out_path.exists()
    df_cols = set(__import__("pandas").read_parquet(out_path).columns)
    expected = {
        "interval_start_utc",
        "node_id",
        "node_name",
        "total_lmp",
        "congestion_price",
        "marginal_loss_price",
        "load",
        "source",
    }
    assert expected.issubset(df_cols)
