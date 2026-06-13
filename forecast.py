from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

TARGET_GRAIN = "Dry Maize__White Maize"
TARGET_COUNTIES = ["Kiambu", "Kirinyaga", "Mombasa", "Nairobi", "Uasin-Gishu"]
FORECAST_DATES = [pd.Timestamp("2025-12-22"), pd.Timestamp("2025-12-29")]
LAG_STEPS = [1, 2, 3, 4, 5, 6, 8]
GLOBAL_LAG_STEPS = [1, 2, 3, 4]


@dataclass
class TrainingArtifacts:
    model: Pipeline
    feature_columns: list[str]
    validation_metrics: dict[str, float]


def load_training_history(parquet_path: str | Path) -> pd.DataFrame:
    df = pd.read_parquet(parquet_path).copy()
    df["year_week"] = pd.to_datetime(df["year_week"])
    df = df[
        (df["grain"] == TARGET_GRAIN)
        & (df["County"].isin(TARGET_COUNTIES))
    ].copy()

    return (
        df[["County", "year_week", "price_mean"]]
        .sort_values(["County", "year_week"])
        .reset_index(drop=True)
    )


def load_observed_window(csv_path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path).copy()
    df["year_week"] = pd.to_datetime(df["Date"])
    df["price_mean"] = pd.to_numeric(df["WholeSale"], errors="coerce")
    return (
        df[["County", "year_week", "price_mean"]]
        .dropna(subset=["price_mean"])
        .sort_values(["County", "year_week"])
        .reset_index(drop=True)
    )


def _add_calendar_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    iso = out["year_week"].dt.isocalendar()
    out["week"] = iso.week.astype(int)
    out["year"] = iso.year.astype(int)
    out["month"] = out["year_week"].dt.month.astype(int)
    out["quarter"] = out["year_week"].dt.quarter.astype(int)
    out["sin_week"] = np.sin(2 * np.pi * out["week"] / 52)
    out["cos_week"] = np.cos(2 * np.pi * out["week"] / 52)
    out["sin_month"] = np.sin(2 * np.pi * out["month"] / 12)
    out["cos_month"] = np.cos(2 * np.pi * out["month"] / 12)
    return out


def build_supervised_frame(history: pd.DataFrame) -> pd.DataFrame:
    df = history.copy().sort_values(["County", "year_week"]).reset_index(drop=True)
    df["global_price"] = df.groupby("year_week")["price_mean"].transform("mean")

    for lag in LAG_STEPS:
        df[f"price_lag_{lag}"] = df.groupby("County")["price_mean"].shift(lag)

    for lag in GLOBAL_LAG_STEPS:
        df[f"global_price_lag_{lag}"] = df.groupby("County")["global_price"].shift(lag)

    grouped = df.groupby("County")["price_mean"]
    shifted = grouped.shift(1)
    df["rolling_mean_3"] = shifted.groupby(df["County"]).transform(lambda s: s.rolling(3).mean())
    df["rolling_mean_6"] = shifted.groupby(df["County"]).transform(lambda s: s.rolling(6).mean())
    df["rolling_std_3"] = shifted.groupby(df["County"]).transform(lambda s: s.rolling(3).std())
    df["rolling_std_6"] = shifted.groupby(df["County"]).transform(lambda s: s.rolling(6).std())
    df["price_diff_1"] = df["price_lag_1"] - df["price_lag_2"]
    df["price_diff_2"] = df["price_lag_2"] - df["price_lag_3"]
    df["price_trend_3"] = df["price_lag_1"] - df["price_lag_3"]
    df["county_vs_global"] = df["price_lag_1"] / (df["global_price_lag_1"] + 1e-6)
    df = _add_calendar_features(df)
    df["target_price"] = df.groupby("County")["price_mean"].shift(-1)
    df["target_delta"] = df["target_price"] - df["price_lag_1"]

    return df.dropna().reset_index(drop=True)


def train_forecaster(history: pd.DataFrame) -> TrainingArtifacts:
    supervised = build_supervised_frame(history)
    unique_weeks = sorted(supervised["year_week"].unique())
    val_weeks = set(unique_weeks[-12:])

    feature_columns = [
        "County",
        "year_week",
        "week",
        "year",
        "month",
        "quarter",
        "sin_week",
        "cos_week",
        "sin_month",
        "cos_month",
        *[f"price_lag_{lag}" for lag in LAG_STEPS],
        *[f"global_price_lag_{lag}" for lag in GLOBAL_LAG_STEPS],
        "rolling_mean_3",
        "rolling_mean_6",
        "rolling_std_3",
        "rolling_std_6",
        "price_diff_1",
        "price_diff_2",
        "price_trend_3",
        "county_vs_global",
    ]

    train_df = supervised[~supervised["year_week"].isin(val_weeks)].copy()
    val_df = supervised[supervised["year_week"].isin(val_weeks)].copy()

    X_train = train_df[feature_columns].copy()
    X_val = val_df[feature_columns].copy()
    y_train = train_df["target_delta"]
    y_val = val_df["target_delta"]

    date_origin = history["year_week"].min()
    for frame in (X_train, X_val):
        frame["year_week"] = (frame["year_week"] - date_origin).dt.days.astype(int)

    preprocessor = ColumnTransformer(
        transformers=[
            ("county", OneHotEncoder(handle_unknown="ignore"), ["County"]),
            ("numeric", Pipeline([("imputer", SimpleImputer(strategy="median"))]), [c for c in feature_columns if c != "County"]),
        ]
    )

    model = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            (
                "regressor",
                RandomForestRegressor(
                    n_estimators=500,
                    random_state=42,
                    min_samples_leaf=2,
                    n_jobs=-1,
                ),
            ),
        ]
    )
    model.fit(X_train, y_train)

    delta_pred = model.predict(X_val)
    price_pred = val_df["price_lag_1"].to_numpy() + delta_pred
    actual_price = val_df["target_price"].to_numpy()
    metrics = {
        "mae": float(mean_absolute_error(actual_price, price_pred)),
        "rmse": float(np.sqrt(mean_squared_error(actual_price, price_pred))),
    }

    model.date_origin_ = date_origin
    return TrainingArtifacts(model=model, feature_columns=feature_columns, validation_metrics=metrics)


def _global_history_map(history: pd.DataFrame) -> dict[pd.Timestamp, float]:
    grouped = history.groupby("year_week")["price_mean"].mean().sort_index()
    return {pd.Timestamp(k): float(v) for k, v in grouped.items()}


def _feature_row_for_forecast(
    county: str,
    target_date: pd.Timestamp,
    county_history: pd.DataFrame,
    global_history: dict[pd.Timestamp, float],
) -> dict[str, float | int | str | pd.Timestamp]:
    county_history = county_history.sort_values("year_week")
    prices = county_history["price_mean"].tolist()
    if len(prices) < max(LAG_STEPS):
        raise ValueError(f"Insufficient history for {county}")

    feature_row: dict[str, float | int | str | pd.Timestamp] = {
        "County": county,
        "year_week": target_date,
    }

    for lag in LAG_STEPS:
        feature_row[f"price_lag_{lag}"] = float(prices[-lag])

    for lag in GLOBAL_LAG_STEPS:
        lag_date = target_date - pd.Timedelta(weeks=lag)
        feature_row[f"global_price_lag_{lag}"] = float(global_history[lag_date])

    last_3 = prices[-3:]
    last_6 = prices[-6:]
    feature_row["rolling_mean_3"] = float(np.mean(last_3))
    feature_row["rolling_mean_6"] = float(np.mean(last_6))
    feature_row["rolling_std_3"] = float(np.std(last_3, ddof=1)) if len(last_3) > 1 else 0.0
    feature_row["rolling_std_6"] = float(np.std(last_6, ddof=1)) if len(last_6) > 1 else 0.0
    feature_row["price_diff_1"] = float(prices[-1] - prices[-2])
    feature_row["price_diff_2"] = float(prices[-2] - prices[-3])
    feature_row["price_trend_3"] = float(prices[-1] - prices[-3])
    feature_row["county_vs_global"] = float(prices[-1] / (global_history[target_date - pd.Timedelta(weeks=1)] + 1e-6))

    temp_df = _add_calendar_features(pd.DataFrame([{"year_week": target_date}]))
    for col in ["week", "year", "month", "quarter", "sin_week", "cos_week", "sin_month", "cos_month"]:
        feature_row[col] = temp_df.iloc[0][col]

    return feature_row


def recursive_forecast(
    artifacts: TrainingArtifacts,
    history: pd.DataFrame,
    forecast_dates: list[pd.Timestamp] | None = None,
) -> pd.DataFrame:
    forecast_dates = forecast_dates or FORECAST_DATES
    working_history = history.copy().sort_values(["County", "year_week"]).reset_index(drop=True)
    global_history = _global_history_map(working_history)
    forecasts: list[dict[str, float | str | int | pd.Timestamp]] = []

    for target_date in forecast_dates:
        feature_rows = []
        for county in TARGET_COUNTIES:
            county_history = working_history[working_history["County"] == county]
            feature_rows.append(
                _feature_row_for_forecast(
                    county=county,
                    target_date=target_date,
                    county_history=county_history,
                    global_history=global_history,
                )
            )

        X_pred = pd.DataFrame(feature_rows)[artifacts.feature_columns].copy()
        X_pred["year_week"] = (pd.to_datetime(X_pred["year_week"]) - artifacts.model.date_origin_).dt.days.astype(int)
        delta_pred = artifacts.model.predict(X_pred)
        price_pred = X_pred["price_lag_1"].to_numpy() + delta_pred

        week_predictions = []
        for county, predicted_price in zip(TARGET_COUNTIES, price_pred):
            week_num = int(pd.Timestamp(target_date).isocalendar().week)
            week_predictions.append(
                {
                    "County": county,
                    "year_week": pd.Timestamp(target_date),
                    "WeekofYear": week_num,
                    "Target_RMSE": round(float(predicted_price), 2),
                    "Target_MAE": round(float(predicted_price), 2),
                }
            )
            working_history = pd.concat(
                [
                    working_history,
                    pd.DataFrame(
                        [{"County": county, "year_week": pd.Timestamp(target_date), "price_mean": float(predicted_price)}]
                    ),
                ],
                ignore_index=True,
            )

        global_history[pd.Timestamp(target_date)] = float(np.mean(price_pred))
        forecasts.extend(week_predictions)

    forecast_df = pd.DataFrame(forecasts)
    forecast_df["ID"] = forecast_df["County"] + "_Week_" + forecast_df["WeekofYear"].astype(str)
    return forecast_df[["ID", "Target_RMSE", "Target_MAE", "County", "year_week", "WeekofYear"]]


def build_final_submission(
    parquet_path: str | Path,
    observed_csv_path: str | Path,
    output_path: str | Path,
) -> tuple[pd.DataFrame, dict[str, float]]:
    training_history = load_training_history(parquet_path)
    artifacts = train_forecaster(training_history)

    observed = load_observed_window(observed_csv_path)
    seed_history = (
        pd.concat([training_history, observed], ignore_index=True)
        .sort_values(["County", "year_week"])
        .drop_duplicates(subset=["County", "year_week"], keep="last")
        .reset_index(drop=True)
    )

    forecast_df = recursive_forecast(artifacts, seed_history)
    observed_submission = observed.copy()
    observed_submission["WeekofYear"] = observed_submission["year_week"].dt.isocalendar().week.astype(int)
    observed_submission["ID"] = observed_submission["County"] + "_Week_" + observed_submission["WeekofYear"].astype(str)
    observed_submission["Target_RMSE"] = observed_submission["price_mean"].round(2)
    observed_submission["Target_MAE"] = observed_submission["price_mean"].round(2)

    final_submission = pd.concat(
        [
            observed_submission[["ID", "Target_RMSE", "Target_MAE"]],
            forecast_df[["ID", "Target_RMSE", "Target_MAE"]],
        ],
        ignore_index=True,
    )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    final_submission.to_csv(output_path, index=False)
    return final_submission, artifacts.validation_metrics
