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
        "feature_importance": read_csv(OUTPUTS / "model_feature_importance.csv"),
        "corr": read_csv(OUTPUTS / "correlation_matrix.csv", index_col=0),
        "context_corr": read_csv(OUTPUTS / "country_context_correlation.csv", index_col=0),
        "country_context": query("select * from mart_country_macro_context"),
        "geo_context": read_csv(PROCESSED / "country_geo_context.csv"),
        "focus_points": read_csv(OUTPUTS / "country_focus_points.csv"),
        "geo_distribution": read_csv(OUTPUTS / "geo_distribution_by_year_region.csv"),
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


def world_geo_heatmap() -> None:
    data = load_data()
    geo = data["geo_context"]
    focus = data["focus_points"]
    distribution = data["geo_distribution"]
    yearly = data["yearly"]
    st.title("World Geo Heatmap & Focus Points")
    st.caption("Country-year geographic view of fuel variation, disasters, conflicts, population and retail pump prices.")
    if geo.empty:
        st.warning("No geographic context available. Run the pipeline first.")
        return
    geo = geo.copy()
    geo["country_code"] = geo["country_code"].astype("string").str.strip()
    geo.loc[geo["country_code"].isin(["", "nan", "None", "<NA>"]), "country_code"] = pd.NA
    geo["is_mappable_country"] = geo["country_code"].notna() & geo["country_code"].str.fullmatch(r"[A-Z]{3}", na=False) & ~geo["country_code"].str.startswith("OWID_", na=False)
    mappable_geo = geo[geo["is_mappable_country"]].copy()

    metric_labels = {
        "disaster_damage_usd": "Disaster damage, USD",
        "conflict_deaths": "Conflict deaths",
        "population_total": "Population",
        "population_pct_change": "Population change, %",
        "gasoline_pump_price_usd_liter": "Gasoline pump price, USD/liter",
        "diesel_pump_price_usd_liter": "Diesel pump price, USD/liter",
        "gasoline_price_pct_change": "Gasoline pump price change, %",
        "diesel_price_pct_change": "Diesel pump price change, %",
    }
    metrics = list(metric_labels)
    availability = {metric: int(pd.to_numeric(mappable_geo[metric], errors="coerce").notna().sum()) for metric in metrics if metric in mappable_geo.columns}
    default_metric = next((m for m in ["disaster_damage_usd", "conflict_deaths", "population_total"] if availability.get(m, 0) > 0), metrics[0])
    metric = st.selectbox(
        "Map metric",
        metrics,
        index=metrics.index(default_metric),
        format_func=lambda value: f"{metric_labels[value]} ({availability.get(value, 0):,} values)",
    )
    mappable_geo[metric] = pd.to_numeric(mappable_geo[metric], errors="coerce")
    valid_years = sorted(mappable_geo.loc[mappable_geo[metric].notna(), "year"].dropna().astype(int).unique())
    if not valid_years:
        st.warning(
            "This country-level metric has no coverage in the current public source. "
            "Use disasters, conflicts or population, or add a richer retail fuel-price source by country."
        )
        st.dataframe(pd.DataFrame({"metric": list(availability), "non_null_values": list(availability.values())}), width="stretch", hide_index=True)
        return

    year_coverage = mappable_geo[mappable_geo[metric].notna()].groupby("year").size()
    default_year = int(year_coverage.idxmax()) if not year_coverage.empty else max(valid_years)
    selected_year = st.slider("Map year", min(valid_years), max(valid_years), default_year)
    selected = mappable_geo[mappable_geo["year"] == selected_year].copy()
    selected[metric] = pd.to_numeric(selected[metric], errors="coerce")
    map_data = selected.dropna(subset=[metric])
    if map_data.empty:
        closest_year = max((year for year in valid_years if year <= selected_year), default=valid_years[-1])
        selected_year = closest_year
        selected = mappable_geo[mappable_geo["year"] == selected_year].copy()
        map_data = selected.dropna(subset=[metric])

    top_focus = map_data.reindex(map_data[metric].abs().sort_values(ascending=False).index).head(25).copy()
    top_focus["focus_size"] = top_focus[metric].abs().fillna(0)
    if not top_focus.empty and top_focus["focus_size"].max() == 0:
        top_focus["focus_size"] = 1
    c = st.columns(4)
    c[0].metric("Countries on map", map_data["country"].nunique())
    c[1].metric("Year", selected_year)
    c[2].metric("Metric average", round(float(map_data[metric].mean()), 3) if not map_data.empty else "n/a")
    c[3].metric("Focus points", len(top_focus))

    st.plotly_chart(
        px.choropleth(
            map_data,
            locations="country_code",
            locationmode="ISO-3",
            color=metric,
            hover_name="country",
            hover_data=["continent", "gasoline_pump_price_usd_liter", "diesel_pump_price_usd_liter", "disaster_damage_usd", "conflict_deaths", "population_total"],
            color_continuous_scale="Turbo",
            title=f"World heatmap: {metric_labels[metric]} in {selected_year}",
        ),
        width="stretch",
    )
    if not top_focus.empty:
        st.plotly_chart(
            px.scatter_geo(
                top_focus,
                locations="country_code",
                locationmode="ISO-3",
                size="focus_size",
                color=metric,
                hover_name="country",
                hover_data=["continent", "gasoline_price_pct_change", "diesel_price_pct_change", "disaster_damage_usd", "conflict_deaths"],
                projection="natural earth",
                title="Focus points: highest absolute metric values",
                color_continuous_scale="Reds",
            ),
            width="stretch",
        )

    st.subheader("Variation through time")
    countries = sorted(geo["country"].dropna().unique())
    defaults = [c for c in ["United States", "Portugal", "Germany", "China", "World"] if c in countries]
    selected_countries = st.multiselect("Countries for variation chart", countries, default=defaults)
    series = geo[geo["country"].isin(selected_countries)] if selected_countries else geo
    st.plotly_chart(px.line(series, x="year", y=metric, color="country", title=f"{metric} variation over time"), width="stretch")

    st.subheader("Statistical view")
    numeric = geo[metrics].apply(pd.to_numeric, errors="coerce")
    st.plotly_chart(px.imshow(numeric.corr(), text_auto=True, aspect="auto", title="Geographic context correlation heatmap"), width="stretch")

    st.subheader("Distribution by year, region and country")
    if not distribution.empty:
        distribution_metric = st.selectbox(
            "Regional distribution metric",
            ["disaster_damage_usd", "conflict_deaths", "population_total", "avg_gasoline_pump_price", "avg_diesel_pump_price"],
            format_func=lambda value: value.replace("_", " ").title(),
        )
        distribution[distribution_metric] = pd.to_numeric(distribution[distribution_metric], errors="coerce")
        regional = distribution.dropna(subset=[distribution_metric])
        if regional.empty:
            st.info("No regional values are available for this metric in the current dataset.")
        else:
            st.plotly_chart(
                px.area(regional, x="year", y=distribution_metric, color="continent", title=f"{distribution_metric} by year and region"),
                width="stretch",
            )
            st.plotly_chart(
                px.bar(regional[regional["year"] == int(regional["year"].max())], x="continent", y=distribution_metric, color="continent", title=f"Latest regional distribution: {distribution_metric}"),
                width="stretch",
            )
    if not yearly.empty:
        fuel_series = sorted(yearly["series"].dropna().unique())
        chosen_series = st.multiselect("Global fuel series for annual comparison", fuel_series, default=fuel_series[:5])
        yearly_metric_labels = {
            "fuel_price_avg": "Average price",
            "fuel_yoy_avg": "Average YoY change",
            "fuel_volatility": "Volatility",
            "jump_count": "Jump months",
        }
        fuel_metric = st.selectbox(
            "Global fuel metric",
            list(yearly_metric_labels),
            format_func=lambda value: yearly_metric_labels[value],
        )
        annual_fuel = yearly[yearly["series"].isin(chosen_series)] if chosen_series else yearly
        st.plotly_chart(px.line(annual_fuel, x="year", y=fuel_metric, color="series", title=f"Global fuel {yearly_metric_labels[fuel_metric]} by year"), width="stretch")

    st.dataframe(top_focus.sort_values(metric, ascending=False), width="stretch", hide_index=True)
    if not focus.empty:
        st.download_button("Download focus points CSV", focus.to_csv(index=False), "country_focus_points.csv", "text/csv")


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
    feature_importance = data["feature_importance"]
    st.title("Forecasting & Export")
    st.caption("Baseline forecast, model evaluation and feature importance for fuel-price jump analysis.")
    st.dataframe(metrics, width="stretch", hide_index=True)
    if not feature_importance.empty:
        st.plotly_chart(
            px.bar(
                feature_importance.sort_values("importance", ascending=False),
                x="feature",
                y="importance",
                color="model",
                barmode="group",
                title="Machine learning feature importance",
            ),
            width="stretch",
        )
    if not forecast.empty:
        selected = st.multiselect("Forecast series", sorted(forecast["series"].unique()), default=sorted(forecast["series"].unique())[:6])
        f = forecast[forecast["series"].isin(selected)]
        st.plotly_chart(px.line(f, x="forecast_month", y="baseline_forecast", color="series", title="36-month baseline forecast"), width="stretch")
        bands = f.melt(
            id_vars=["series", "forecast_month"],
            value_vars=[col for col in ["lower_band", "baseline_forecast", "upper_band"] if col in f.columns],
            var_name="forecast_band",
            value_name="value",
        )
        st.plotly_chart(px.line(bands, x="forecast_month", y="value", color="series", line_dash="forecast_band", title="Forecast bands: lower, baseline and upper"), width="stretch")
        st.plotly_chart(px.bar(f.drop_duplicates("series"), x="series", y="historical_jump_risk", title="Historical jump risk used by the forecast"), width="stretch")
        st.info(
            "Forecast method: 12-month average plus recent year-over-year trend, with a volatility band. "
            "It is a transparent baseline for decision support, not a causal model of wars or catastrophes."
        )
    export = data["global_features"]
    st.download_button("Download global decision features CSV", export.to_csv(index=False), "global_fuel_decision_features.csv", "text/csv")
    st.download_button("Download forecast CSV", forecast.to_csv(index=False), "global_fuel_forecast.csv", "text/csv")


PAGES = {
    "Overview": overview,
    "Price Series Explorer": price_series,
    "Shock Detection & Events": shocks_events,
    "World Geo Heatmap": world_geo_heatmap,
    "Country Context": country_context,
    "Correlation Analysis": correlations,
    "Forecasting & Export": forecasting_export,
}


def run_app() -> None:
    st.set_page_config(page_title="Global Fuel Shocks Intelligence", page_icon="Fuel", layout="wide")
    page = st.sidebar.radio("Page", list(PAGES))
    PAGES[page]()
