# Global Fuel Shocks Intelligence

Global Fuel Shocks Intelligence is a reproducible analytics project for studying fuel-price variation, volatility and jump risk across time.

The study links fuel prices with:

- wars and armed conflict
- natural disasters and economic damage
- population by country and globally
- residential house-price variation
- macro-level event windows

The project is prepared for:

- DuckDB analytical storage
- dbt transformation and tests
- statistical analysis
- forecasting and jump-risk modelling
- Streamlit exploration and export
- HTML reporting

## Key Question

How do global and country-level fuel prices vary over time, and how are major price jumps associated with wars, disasters, population growth and housing-market variation?

## Architecture

```text
Public data sources
  -> raw CSV/XLSX/API extracts
  -> processed normalized tables
  -> DuckDB analytical database
  -> dbt staging/intermediate/marts
  -> statistics and forecasts
  -> Streamlit app and HTML report
```

## Data Sources

Planned and partially automated:

- World Bank Pink Sheet commodity prices
- World Bank indicators API
- Our World in Data / EM-DAT disaster data
- Our World in Data / UCDP armed conflict data
- BIS residential property prices or public mirror datasets

## How To Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 scripts/run_pipeline.py
streamlit run app.py --server.port 8590
```

For dbt:

```bash
python3 -m venv .venv-dbt
source .venv-dbt/bin/activate
pip install -r requirements-dbt.txt
cd dbt_fuel_shocks
dbt build --profiles-dir .
```

## Outputs

- `data/processed/fuel_shocks.duckdb`
- `data/processed/*.csv`
- `data/outputs/statistical_summary.csv`
- `data/outputs/correlation_matrix.csv`
- `data/outputs/event_study_summary.csv`
- `data/outputs/forecast_baseline.csv`

## Streamlit App

Run:

```bash
streamlit run app.py --server.port 8590
```

Pages:

- Overview
- Price Series Explorer
- Shock Detection & Events
- World Geo Heatmap
- Country Context
- Correlation Analysis
- Forecasting & Export

## Methodology

The analysis uses:

- price returns and percentage changes
- rolling volatility
- z-score shock detection
- lagged correlations
- event-study windows
- regression-ready feature tables
- baseline forecasting

## Caution

This project is designed to support structured analysis. It does not claim that wars or disasters automatically cause fuel-price changes. Causal interpretation requires stronger identification strategies and context-specific validation.
