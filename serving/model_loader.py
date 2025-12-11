from pathlib import Path
from typing import Optional

from xgboost import XGBRegressor


_model: Optional[XGBRegressor] = None


def get_model() -> XGBRegressor:
    global _model
    if _model is None:
        model_path = Path("data/models/xgb_rt_lmp.json")
        if not model_path.exists():
            raise RuntimeError(f"Model file not found at {model_path}")
        model = XGBRegressor()
        model.load_model(model_path)
        _model = model
    return _model
