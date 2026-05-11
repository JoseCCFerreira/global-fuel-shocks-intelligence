from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUTPUTS = DATA / "outputs"
PROCESSED = DATA / "processed"
REFERENCE = DATA / "reference"
DB_PATH = PROCESSED / "fuel_shocks.duckdb"


@st.cache_data
def read_csv(path: Path, **kwargs) -> pd.DataFrame:
    return pd.read_csv(path, **kwargs) if path.exists() else pd.DataFrame()


@st.cache_data
def query(sql: str) -> pd.DataFrame:
    if not DB_PATH.exists():
        return pd.DataFrame()
    with duckdb.connect(str(DB_PATH)) as conn:
        return conn.execute(sql).fetchdf()


def load_data() -> dict[str, pd.DataFrame]:
    return {
        "fuel": read_csv(PROCESSED / "fuel_price_features.csv", parse_dates=["date", "month"]),
        "yearly": read_csv(PROCESSED / "fuel_yearly_features.csv"),
        "stats": read_csv(OUTPUTS / "statistical_summary.csv"),
        "events": read_csv(OUTPUTS / "event_study_summary.csv"),
        "forecast": read_csv(OUTPUTS / "forecast_baseline.csv", parse_dates=["forecast_month"]),
        "metrics": read_csv(OUTPUTS / "model_metrics.csv"),
        "corr": read_csv(OUTPUTS / "correlation_matrix.csv", index_col=0),
        "context_corr": read_csv(OUTPUTS / "country_context_correlation.csv", index_col=0),
        "country_context": query("select * from mart_country_macro_context"),
        "global_features": query("select * from mart_global_decision_features"),
        "sources": read_csv(REFERENCE / "source_registry.csv"),
    }


def sidebar_filter(fuel: pd.DataFrame) -> pd.DataFrame:
    if fuel.empty:
        return fuel
    series = sorted(fuel["series"].dropna().unique())
    default = [s for s in series if any(key in s.lower() for key in ["crude", "natural gas", "coal", "energy"])][:8]
    selected = st.sidebar.multiselect("Fuel / energy series", series, default=default or series[:6])
    years = sorted(fuel["year"].dropna().astype(int).unique())
    year_range = st.sidebar.slider("Year range", int(min(years)), int(max(years)), (max(1960, int(min(years))), int(max(years))))
    return fuel[fuel["series"].isin(selected) & fuel["year"].between(year_range[0], year_range[1])]


def overview() -> None:
    data = load_data()
    fuel = sidebar_filter(data["fuel"])
    st.title("Global Fuel Shocks Intelligence")
    st.caption("Fuel prices, wars, disasters, population, housing and price-jump risk.")
    if fuel.empty:
        st.warning("No fuel data available. Run `python3 scripts/run_pipeline.py` first.")
        return
    c = st.columns(5)
    c[0].metric("Observations", f"{len(fuel):,}")
    c[1].metric("Series", fuel["series"].nunique())
    c[2].metric("First year", int(fuel["year"].min()))
    c[3].metric("Latest year", int(fuel["year"].max()))
    c[4].metric("Jump months", int(fuel["price_jump_flag"].sum()))
    st.plotly_chart(px.line(fuel, x="month", y="value", color="series", title="Fuel and energy prices over time"), width="stretch")
    st.plotly_chart(px.line(fuel, x="month", y="rolling_12m_volatility", color="series", title="Rolling 12-month volatility"), width="stretch")
    st.subheader("Data sources")
    st.dataframe(data["sources"], width="stretch", hide_index=True)


def price_series() -> None:
    fuel = sidebar_filter(load_data()["fuel"])
    st.title("Price Series Explorer")
    metric = st.selectbox("Metric", ["value", "mom_pct_change", "yoy_pct_change", "rolling_12m_avg", "rolling_12m_volatility", "zscore_mom"])
    st.plotly_chart(px.line(fuel, x="month", y=metric, color="series", title=f"{metric} by series"), width="stretch")
    st.plotly_chart(px.box(fuel.dropna(subset=["mom_pct_change"]), x="series", y="mom_pct_change", title="Monthly change distribution"), width="stretch")
    st.dataframe(fuel.sort_values("month", ascending=False).head(300), width="stretch", hide_index=True)


def shocks_events() -> None:
    data = load_data()
    fuel = sidebar_filter(data["fuel"])
    events = data["events"]
    st.title("Shock Detection & Event Study")
    jumps = fuel[fuel["price_jump_flag"] == 1].copy()
    st.metric("Selected jump months", int(len(jumps)))
    st.plotly_chart(px.scatter(jumps, x="month", y="mom_pct_change", color="series", size=jumps["zscore_mom"].abs(), hover_data=["zscore_mom"], title="Detected fuel price jumps"), width="stretch")
    st.plotly_chart(px.bar(events.sort_values("jump_months", ascending=False).head(40), x="year", y="jump_months", color="series", title="Jump months by year and series"), width="stretch")
    st.dataframe(events.sort_values(["jump_months", "max_abs_zscore"], ascending=False), width="stretch", hide_index=True)


def country_context() -> None:
    data = load_data()
    context = data["country_context"]
    st.title("Country Context: Population, Wars, Disasters & Housing")
    if context.empty:
        st.warning("No country context mart available. Run pipeline and dbt.")
        return
    countries = sorted(context["country"].dropna().unique())
    selected = st.multiselect("Countries", countries, default=[c for c in ["World", "United States", "Portugal", "Germany"] if c in countries])
    df = context[context["country"].isin(selected)] if selected else context
    y = st.selectbox("Context metric", ["population_total", "gasoline_pump_price_usd_liter", "diesel_pump_price_usd_liter", "disaster_damage_usd", "conflict_deaths", "house_price_index"])
    st.plotly_chart(px.line(df, x="year", y=y, color="country", title=f"{y} by country"), width="stretch")
    st.plotly_chart(px.imshow(data["context_corr"], text_auto=True, aspect="auto", title="Country context correlation matrix"), width="stretch")
    st.dataframe(df.sort_values(["country", "year"], ascending=[True, False]).head(500), width="stretch", hide_index=True)


def correlations() -> None:
    data = load_data()
    st.title("Correlation Analysis")
    st.plotly_chart(px.imshow(data["corr"], text_auto=False, aspect="auto", title="Fuel monthly-change correlations"), width="stretch")
    global_features = data["global_features"]
    st.subheader("Global dbt decision features")
    st.dataframe(global_features.sort_values("year", ascending=False).head(300), width="stretch", hide_index=True)


def forecasting_export() -> None:
    data = load_data()
    forecast = data["forecast"]
    metrics = data["metrics"]
    st.title("Forecasting & Export")
    st.caption("Baseline forecast and model evaluation. Future versions can add ARIMA/SARIMAX and regime models.")
    st.dataframe(metrics, width="stretch", hide_index=True)
    if not forecast.empty:
        selected = st.multiselect("Forecast series", sorted(forecast["series"].unique()), default=sorted(forecast["series"].unique())[:6])
        f = forecast[forecast["series"].isin(selected)]
        st.plotly_chart(px.line(f, x="forecast_month", y="baseline_forecast", color="series", title="12-month moving-average forecast"), width="stretch")
    export = data["global_features"]
    st.download_button("Download global decision features CSV", export.to_csv(index=False), "global_fuel_decision_features.csv", "text/csv")
    st.download_button("Download forecast CSV", forecast.to_csv(index=False), "global_fuel_forecast.csv", "text/csv")


PAGES = {
    "Overview": overview,
    "Price Series Explorer": price_series,
    "Shock Detection & Events": shocks_events,
    "Country Context": country_context,
    "Correlation Analysis": correlations,
    "Forecasting & Export": forecasting_export,
}


def run_app() -> None:
    st.set_page_config(page_title="Global Fuel Shocks Intelligence", page_icon="Fuel", layout="wide")
    page = st.sidebar.radio("Page", list(PAGES))
    PAGES[page]()
