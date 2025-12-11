import pandas as pd

from feature_repo.feature_definitions import (
    add_lag_features,
    add_rolling_features,
    add_cyclical_time_features,
    build_features,
)


def sample_df():
    ts = pd.date_range("2025-01-01", periods=500, freq="5min", tz="UTC")
    df = pd.DataFrame(
        {
            "interval_start_utc": ts,
            "total_lmp": 30 + (pd.Series(range(500)) % 15),
            "node_id": 51217,
            "node_name": "SomeNode",
            "congestion_price": 0.5,
            "marginal_loss_price": 0.1,
            "load": 90000,
            "source": "rt_lmp",
        }
    )
    return df


def test_lag_features():
    df = sample_df()
    df2 = add_lag_features(df)
    assert "lmp_lag_1h" in df2.columns
    assert df2["lmp_lag_1h"].isnull().sum() > 0


def test_rolling_features():
    df = sample_df()
    df2 = add_rolling_features(df)
    assert "lmp_rolling_mean_24h" in df2.columns
    assert df2["lmp_rolling_mean_24h"].isnull().sum() > 0


def test_cyclical_time_features():
    df = sample_df()
    df2 = add_cyclical_time_features(df)
    assert "hour_sin" in df2.columns
    assert "dow_cos" in df2.columns


def test_build_features():
    df = sample_df()
    df2 = build_features(df)
    assert df2.shape[0] < df.shape[0]
    assert "hour_sin" in df2.columns
    assert "lmp_lag_24h" in df2.columns
