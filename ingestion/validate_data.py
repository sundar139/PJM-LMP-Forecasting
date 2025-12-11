import argparse
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent))

import great_expectations as gx
from great_expectations.validator.validator import Validator
from great_expectations.execution_engine.pandas_execution_engine import PandasExecutionEngine

from ingestion.config import PROCESSED_DIR


def add_expectations(validator: Validator, df) -> None:
    import pandas as pd
    timestamp_candidates = [
        "interval_start_utc",
        "Interval Start",
        "Time",
    ]
    ts_col = next((c for c in timestamp_candidates if c in df.columns), None)
    required_cols = [ts_col, "source"]
    optional_cols = [
        "node_id",
        "node_name",
        "total_lmp",
        "congestion_price",
        "marginal_loss_price",
        "load",
        "load_forecast",
    ]
    cols_present = required_cols + [c for c in optional_cols if c in df.columns]
    if ts_col:
        validator.expect_column_values_to_not_be_null(column=ts_col)
    validator.expect_column_values_to_be_in_set(
        column="source", value_set=["rt_lmp", "da_lmp", "load_forecast", "load_metered"]
    )

    def _get_col(frame, candidates):
        return next((c for c in candidates if c in frame.columns), None)

    region_col = _get_col(df, ["node_name", "Location Name"])
    def _cond_col(col_name: str) -> str:
        # use backticks for columns with spaces/special chars per pandas eval
        return f"`{col_name}`" if (" " in col_name or not col_name.isidentifier()) else col_name

    if region_col:
        # LMP per-region bounds (data-driven quantiles)
        lmp_col = _get_col(df, ["total_lmp", "LMP"])
        df_lmp = df[df.get("source").isin(["rt_lmp", "da_lmp"])].copy() if "source" in df.columns else None
        if lmp_col and df_lmp is not None and not df_lmp.empty:
            for region in df_lmp[region_col].dropna().unique().tolist():
                sub = df_lmp[df_lmp[region_col] == region]
                if sub.empty:
                    continue
                q01 = sub[lmp_col].quantile(0.01)
                q99 = sub[lmp_col].quantile(0.99)
                rng = float(q99 - q01) if pd.notnull(q01) and pd.notnull(q99) else 0.0
                if rng <= 0:
                    continue
                min_v = float(q01 - 0.1 * rng)
                max_v = float(q99 + 0.1 * rng)
                region_safe = str(region).replace('"', '\\"')
                rc = _cond_col(region_col)
                cond = f"source.isin([\"rt_lmp\",\"da_lmp\"]) & ({rc}==\"{region_safe}\")"
                validator.expect_column_values_to_be_between(
                    column=lmp_col,
                    min_value=min_v,
                    max_value=max_v,
                    mostly=0.98,
                    row_condition=cond,
                    condition_parser="pandas",
                )

        # Metered load per-region bounds
        load_col = _get_col(df, ["load", "Load"])
        df_metered = df[df.get("source") == "load_metered"].copy() if "source" in df.columns else None
        if load_col and df_metered is not None and not df_metered.empty:
            for region in df_metered[region_col].dropna().unique().tolist():
                sub = df_metered[df_metered[region_col] == region]
                if sub.empty:
                    continue
                q01 = sub[load_col].quantile(0.01)
                q99 = sub[load_col].quantile(0.99)
                rng = float(q99 - q01) if pd.notnull(q01) and pd.notnull(q99) else 0.0
                if rng <= 0:
                    continue
                min_v = max(0.0, float(q01 - 0.1 * rng))
                max_v = float(q99 + 0.1 * rng)
                region_safe = str(region).replace('"', '\\"')
                rc = _cond_col(region_col)
                cond = f"source==\"load_metered\" & ({rc}==\"{region_safe}\")"
                validator.expect_column_values_to_be_between(
                    column=load_col,
                    min_value=min_v,
                    max_value=max_v,
                    mostly=0.98,
                    row_condition=cond,
                    condition_parser="pandas",
                )

        # Forecast load per-region bounds
        lf_col = _get_col(df, ["load_forecast", "Load Forecast"])
        df_forecast = df[df.get("source") == "load_forecast"].copy() if "source" in df.columns else None
        if lf_col and df_forecast is not None and not df_forecast.empty:
            for region in df_forecast[region_col].dropna().unique().tolist():
                sub = df_forecast[df_forecast[region_col] == region]
                if sub.empty:
                    continue
                q01 = sub[lf_col].quantile(0.01)
                q99 = sub[lf_col].quantile(0.99)
                rng = float(q99 - q01) if pd.notnull(q01) and pd.notnull(q99) else 0.0
                if rng <= 0:
                    continue
                min_v = max(0.0, float(q01 - 0.1 * rng))
                max_v = float(q99 + 0.1 * rng)
                region_safe = str(region).replace('"', '\\"')
                rc = _cond_col(region_col)
                cond = f"source==\"load_forecast\" & ({rc}==\"{region_safe}\")"
                validator.expect_column_values_to_be_between(
                    column=lf_col,
                    min_value=min_v,
                    max_value=max_v,
                    mostly=0.98,
                    row_condition=cond,
                    condition_parser="pandas",
                )


def validate_file(processed_path: Path) -> None:
    print(f"Validating {processed_path}")
    import pandas as pd
    df = pd.read_parquet(processed_path)
    context = gx.get_context()
    pandas_ds = context.sources.add_or_update_pandas(name="local_pandas")
    asset = pandas_ds.add_dataframe_asset(name="processed_df")
    batch_request = asset.build_batch_request(dataframe=df)
    validator = context.get_validator(batch_request=batch_request)
    add_expectations(validator, df)
    result = validator.validate()
    if not result["success"]:
        raise SystemExit("Data validation failed")

    def _get_col(frame, candidates):
        return next((c for c in candidates if c in frame.columns), None)

    # Source-specific validations
    overall_success = True
    # LMP expectations for rt_lmp and da_lmp
    df_lmp = df[df.get("source").isin(["rt_lmp", "da_lmp"])].copy() if "source" in df.columns else pd.DataFrame()
    if not df_lmp.empty:
        asset_lmp = pandas_ds.add_dataframe_asset(name="processed_df_lmp")
        br_lmp = asset_lmp.build_batch_request(dataframe=df_lmp)
        v_lmp = context.get_validator(batch_request=br_lmp)
        lmp_col = _get_col(df_lmp, ["total_lmp", "LMP"])  # processed or raw
        if lmp_col:
            v_lmp.expect_column_values_to_not_be_null(column=lmp_col)
            v_lmp.expect_column_values_to_be_between(column=lmp_col, min_value=-200, max_value=5000, mostly=0.99)
        res_lmp = v_lmp.validate()
        overall_success = overall_success and res_lmp["success"]

    # Metered load expectations
    df_metered = df[df.get("source") == "load_metered"].copy() if "source" in df.columns else pd.DataFrame()
    if not df_metered.empty:
        asset_m = pandas_ds.add_dataframe_asset(name="processed_df_metered")
        br_m = asset_m.build_batch_request(dataframe=df_metered)
        v_m = context.get_validator(batch_request=br_m)
        load_col = _get_col(df_metered, ["load", "Load"])  # processed or raw
        if load_col:
            v_m.expect_column_values_to_not_be_null(column=load_col)
            v_m.expect_column_values_to_be_between(column=load_col, min_value=0, mostly=0.98)
        res_m = v_m.validate()
        overall_success = overall_success and res_m["success"]

    # Forecast load expectations
    df_forecast = df[df.get("source") == "load_forecast"].copy() if "source" in df.columns else pd.DataFrame()
    if not df_forecast.empty:
        asset_f = pandas_ds.add_dataframe_asset(name="processed_df_forecast")
        br_f = asset_f.build_batch_request(dataframe=df_forecast)
        v_f = context.get_validator(batch_request=br_f)
        lf_col = _get_col(df_forecast, ["load_forecast", "Load Forecast"])  # processed or raw
        if lf_col:
            v_f.expect_column_values_to_not_be_null(column=lf_col)
            v_f.expect_column_values_to_be_between(column=lf_col, min_value=0, mostly=0.98)
        res_f = v_f.validate()
        overall_success = overall_success and res_f["success"]

    if not overall_success:
        raise SystemExit("Data validation failed")
    print("Validation passed.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--processed-path", type=str, required=True)
    args = parser.parse_args()
    validate_file(Path(args.processed_path))


if __name__ == "__main__":
    main()
