from datetime import timedelta

import numpy as np
import pandas as pd


def add_lag_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values("interval_start_utc")
    df["lmp_lag_1h"] = df["total_lmp"].shift(12)  # 12 * 5min = 60 minutes
    df["lmp_lag_24h"] = df["total_lmp"].shift(12 * 24)
    df["lmp_lag_168h"] = df["total_lmp"].shift(12 * 24 * 7)
    return df


def add_rolling_features(df: pd.DataFrame) -> pd.DataFrame:
    window = 12 * 24  # 24h window for 5-min data
    df["lmp_rolling_mean_24h"] = df["total_lmp"].rolling(window=window).mean()
    df["lmp_rolling_std_24h"] = df["total_lmp"].rolling(window=window).std()
    return df


def add_cyclical_time_features(df: pd.DataFrame) -> pd.DataFrame:
    df["hour"] = df["interval_start_utc"].dt.hour
    df["dow"] = df["interval_start_utc"].dt.dayofweek

    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)

    df["dow_sin"] = np.sin(2 * np.pi * df["dow"] / 7)
    df["dow_cos"] = np.cos(2 * np.pi * df["dow"] / 7)
    return df


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = add_lag_features(df)
    df = add_rolling_features(df)
    df = add_cyclical_time_features(df)
    na_ratio = df.isna().mean()
    drop_cols = na_ratio[na_ratio > 0.99].index.tolist()
    if drop_cols:
        df = df.drop(columns=drop_cols)
    df = df.dropna()
    return df
