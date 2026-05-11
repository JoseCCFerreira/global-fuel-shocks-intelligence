from __future__ import annotations

from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import accuracy_score, mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split


ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "data" / "outputs"
DB_PATH = PROCESSED / "fuel_shocks.duckdb"


def main() -> None:
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(DB_PATH))
    fuel = conn.execute("SELECT * FROM raw_fuel_price_features").fetchdf()
    context = conn.execute("SELECT * FROM mart_country_context").fetchdf()

    if not fuel.empty:
        stats = fuel.groupby("series", as_index=False).agg(
            observations=("value", "count"),
            first_date=("date", "min"),
            last_date=("date", "max"),
            avg_price=("value", "mean"),
            max_price=("value", "max"),
            avg_mom_change=("mom_pct_change", "mean"),
            volatility=("mom_pct_change", "std"),
            jumps=("price_jump_flag", "sum"),
        )
        stats.to_csv(OUTPUTS / "statistical_summary.csv", index=False)
        pivot = fuel.pivot_table(index="month", columns="series", values="mom_pct_change", aggfunc="mean")
        pivot.corr().to_csv(OUTPUTS / "correlation_matrix.csv")

        events = fuel[fuel["price_jump_flag"] == 1].copy()
        events.groupby(["series", "year"], as_index=False).agg(
            jump_months=("month", "count"),
            avg_jump_change=("mom_pct_change", "mean"),
            max_abs_zscore=("zscore_mom", lambda s: s.abs().max()),
        ).to_csv(OUTPUTS / "event_study_summary.csv", index=False)

        forecast = []
        for series, group in fuel.sort_values("month").groupby("series"):
            group = group.dropna(subset=["value"]).copy()
            if len(group) < 24:
                continue
            last = group.iloc[-1]
            rolling = group["value"].tail(12).mean()
            for step in range(1, 13):
                forecast.append(
                    {
                        "series": series,
                        "forecast_month": pd.to_datetime(last["month"]) + pd.DateOffset(months=step),
                        "baseline_forecast": rolling,
                        "method": "last_12_month_average",
                    }
                )
        pd.DataFrame(forecast).to_csv(OUTPUTS / "forecast_baseline.csv", index=False)

        ml = fuel.dropna(subset=["mom_pct_change", "rolling_12m_volatility", "yoy_pct_change", "price_jump_flag"]).copy()
        ml["month_number"] = pd.to_datetime(ml["month"]).dt.month
        ml["series_code"] = ml["series"].astype("category").cat.codes
        features = ["value", "rolling_12m_volatility", "yoy_pct_change", "month_number", "series_code"]
        metrics = []
        if len(ml) > 200 and ml["price_jump_flag"].nunique() > 1:
            X_train, X_test, y_train, y_test = train_test_split(ml[features], ml["price_jump_flag"], test_size=0.25, random_state=42, stratify=ml["price_jump_flag"])
            clf = RandomForestClassifier(n_estimators=150, min_samples_leaf=5, random_state=42)
            clf.fit(X_train, y_train)
            pred = clf.predict(X_test)
            metrics.append({"model": "RandomForestClassifier", "target": "price_jump_flag", "accuracy": round(accuracy_score(y_test, pred), 4)})
        if len(ml) > 200:
            reg_data = ml.dropna(subset=["mom_pct_change"])
            X_train, X_test, y_train, y_test = train_test_split(reg_data[features], reg_data["mom_pct_change"], test_size=0.25, random_state=42)
            reg = RandomForestRegressor(n_estimators=150, min_samples_leaf=5, random_state=42)
            reg.fit(X_train, y_train)
            pred = reg.predict(X_test)
            metrics.append({"model": "RandomForestRegressor", "target": "mom_pct_change", "mae": round(mean_absolute_error(y_test, pred), 4), "r2": round(r2_score(y_test, pred), 4)})
        pd.DataFrame(metrics).to_csv(OUTPUTS / "model_metrics.csv", index=False)

    if not context.empty:
        numeric = context.select_dtypes(include=[np.number])
        numeric.corr().to_csv(OUTPUTS / "country_context_correlation.csv")

    conn.close()
    print(f"Analysis outputs written to {OUTPUTS}")


if __name__ == "__main__":
    main()
