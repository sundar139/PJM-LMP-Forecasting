from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = BASE_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)


DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"


@dataclass
class Settings:
    env: str = os.getenv("ENV", "dev")
    aws_region: str = os.getenv("AWS_REGION", "us-east-1")
    s3_bucket_raw: str = os.getenv("S3_BUCKET_RAW", "")
    s3_bucket_processed: str = os.getenv("S3_BUCKET_PROCESSED", "")
    use_s3: bool = os.getenv("USE_S3", "0") == "1"

    pjm_node_id: int = int(os.getenv("PJM_NODE_ID", "51217"))
    pjm_market_rt: str = os.getenv("PJM_MARKET_RT", "REAL_TIME_5_MIN")
    pjm_market_da: str = os.getenv("PJM_MARKET_DA", "DAY_AHEAD_HOURLY")


settings = Settings()


def ensure_local_dirs() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
