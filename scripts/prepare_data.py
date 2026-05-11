from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"


def read_pink_sheet() -> pd.DataFrame:
    path = RAW / "world_bank_pink_sheet_monthly.xlsx"
    if not path.exists():
        return pd.DataFrame(columns=["date", "series", "value"])
    raw = pd.read_excel(path, sheet_name="Monthly Prices", header=None)
    code_row = raw.index[raw.iloc[:, 0].astype(str).str.match(r"^\d{4}M\d{2}$", na=False)]
    if len(code_row) == 0:
        return pd.DataFrame(columns=["date", "series", "value"])
    first_data_row = int(code_row[0])
    names = raw.iloc[first_data_row - 3].fillna(raw.iloc[first_data_row - 1]).astype(str).tolist()
    codes = raw.iloc[first_data_row - 1].astype(str).tolist()
    columns = ["date"] + [f"{code} | {name}" for code, name in zip(codes[1:], names[1:])]
    df = raw.iloc[first_data_row:].copy()
    df = df.iloc[:, : len(columns)]
    df.columns = columns
    df["date"] = pd.to_datetime(df["date"].astype(str).str.replace("M", "-", regex=False) + "-01", errors="coerce")
    df = df.dropna(subset=["date"])
    long = df.melt(id_vars=["date"], var_name="series", value_name="value")
    long["value"] = long["value"].replace({"…": np.nan, "..": np.nan, "": np.nan})
    long["value"] = pd.to_numeric(long["value"], errors="coerce")
    long = long.dropna(subset=["value"])
    long["series"] = long["series"].astype(str).str.strip()
    return long


def read_world_bank_indicators() -> pd.DataFrame:
    frames = []
    for path in RAW.glob("world_bank_*.csv"):
        if path.name == "world_bank_pink_sheet_monthly.xlsx":
            continue
        try:
            frames.append(pd.read_csv(path))
        except Exception:
            continue
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def normalize_owid(path: Path, value_name: str) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=["country", "country_code", "year", value_name])
    df = pd.read_csv(path)
    columns = {c.lower(): c for c in df.columns}
    country_col = columns.get("entity", df.columns[0])
    code_col = columns.get("code", None)
    year_col = columns.get("year", None)
    value_cols = [c for c in df.columns if c not in {country_col, code_col, year_col}]
    if not year_col or not value_cols:
        return pd.DataFrame(columns=["country", "country_code", "year", value_name])
    value_col = value_cols[-1]
    out = df[[country_col, year_col, value_col] + ([code_col] if code_col else [])].copy()
    out = out.rename(columns={country_col: "country", year_col: "year", value_col: value_name})
    out["country_code"] = out[code_col] if code_col else None
    out[value_name] = pd.to_numeric(out[value_name], errors="coerce")
    return out[["country", "country_code", "year", value_name]].dropna(subset=[value_name])


def normalize_house_prices() -> pd.DataFrame:
    path = RAW / "house_prices_global.csv"
    if not path.exists():
        return pd.DataFrame(columns=["country", "year", "house_price_index"])
    df = pd.read_csv(path)
    lower = {c.lower(): c for c in df.columns}
    year_col = lower.get("year") or lower.get("time") or df.columns[0]
    country_col = lower.get("country") or lower.get("location") or lower.get("reference area") or df.columns[1]
    value_col = lower.get("value") or df.columns[-1]
    out = df[[country_col, year_col, value_col]].copy()
    out = out.rename(columns={country_col: "country", year_col: "year", value_col: "house_price_index"})
    out["year"] = pd.to_numeric(out["year"], errors="coerce")
    out["house_price_index"] = pd.to_numeric(out["house_price_index"], errors="coerce")
    return out.dropna(subset=["year", "house_price_index"])


def country_geo_reference(wb: pd.DataFrame) -> pd.DataFrame:
    countries = wb[["country_code", "country"]].dropna().drop_duplicates()
    try:
        import plotly.express as px

        geo = px.data.gapminder()[["iso_alpha", "country", "continent"]].drop_duplicates()
        geo = geo.rename(columns={"iso_alpha": "country_code", "country": "plotly_country"})
        countries = countries.merge(geo, on="country_code", how="left")
    except Exception:
        countries["plotly_country"] = None
        countries["continent"] = None
    return countries


def build_features(fuel: pd.DataFrame) -> pd.DataFrame:
    if fuel.empty:
        return fuel
    selected = fuel[fuel["series"].str.contains("crude|oil|gas|diesel|coal|energy", case=False, na=False)].copy()
    selected = selected.sort_values(["series", "date"])
    selected["month"] = selected["date"].dt.to_period("M").dt.to_timestamp()
    selected["year"] = selected["date"].dt.year
    selected["mom_pct_change"] = selected.groupby("series")["value"].pct_change() * 100
    selected["yoy_pct_change"] = selected.groupby("series")["value"].pct_change(12) * 100
    selected["rolling_12m_avg"] = selected.groupby("series")["value"].transform(lambda s: s.rolling(12, min_periods=3).mean())
    selected["rolling_12m_volatility"] = selected.groupby("series")["mom_pct_change"].transform(lambda s: s.rolling(12, min_periods=6).std())
    selected["zscore_mom"] = selected.groupby("series")["mom_pct_change"].transform(lambda s: (s - s.mean()) / s.std(ddof=0))
    selected["price_jump_flag"] = (selected["zscore_mom"].abs() >= 2.5).astype(int)
    return selected


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    fuel = read_pink_sheet()
    fuel_features = build_features(fuel)
    wb = read_world_bank_indicators()
    disasters = normalize_owid(RAW / "owid_disaster_damage.csv", "disaster_damage_usd")
    conflicts = normalize_owid(RAW / "owid_conflict_deaths.csv", "conflict_deaths")
    houses = normalize_house_prices()
    geo = country_geo_reference(wb)

    fuel.to_csv(PROCESSED / "fuel_prices_long.csv", index=False)
    fuel_features.to_csv(PROCESSED / "fuel_price_features.csv", index=False)
    wb.to_csv(PROCESSED / "world_bank_indicators.csv", index=False)
    disasters.to_csv(PROCESSED / "disaster_damage.csv", index=False)
    conflicts.to_csv(PROCESSED / "conflict_deaths.csv", index=False)
    houses.to_csv(PROCESSED / "house_prices.csv", index=False)
    geo.to_csv(PROCESSED / "country_geo_reference.csv", index=False)

    yearly_fuel = fuel_features.groupby(["year", "series"], as_index=False).agg(
        fuel_price_avg=("value", "mean"),
        fuel_yoy_avg=("yoy_pct_change", "mean"),
        fuel_volatility=("mom_pct_change", "std"),
        jump_count=("price_jump_flag", "sum"),
    )
    yearly_fuel.to_csv(PROCESSED / "fuel_yearly_features.csv", index=False)
    print("Processed data written to", PROCESSED)


if __name__ == "__main__":
    main()
