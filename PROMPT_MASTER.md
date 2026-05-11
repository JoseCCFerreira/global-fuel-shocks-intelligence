# Master Prompt - Global Fuel Shocks Intelligence

Build a professional, reproducible analytics project called **Global Fuel Shocks Intelligence**.

The goal is to study global fuel-price variation since systematic tracking began, correlate fuel shocks with wars, natural disasters, population, and residential house-price variation, and forecast future price fluctuations or sudden jumps.

The project must:

1. Collect public and reproducible data:
   - monthly global commodity fuel prices from the World Bank Pink Sheet
   - country-level gasoline and diesel pump prices from World Bank indicators when available
   - population by country and world total from World Bank
   - natural disasters and economic damage from Our World in Data / EM-DAT
   - armed conflict deaths from Our World in Data / UCDP where available
   - residential house-price indexes from BIS or public mirror datasets

2. Store raw, processed, and curated data:
   - `data/raw`
   - `data/processed`
   - `data/outputs`
   - `data/reference`

3. Import analytical data into DuckDB:
   - one analytical database in `data/processed/fuel_shocks.duckdb`
   - raw tables
   - integrated time-series tables
   - mart tables ready for dashboard and modelling

4. Use dbt with DuckDB:
   - staging models
   - intermediate feature models
   - marts
   - schema tests
   - documentation

5. Analyse:
   - long-run fuel-price trends
   - month-over-month and year-over-year variation
   - volatility
   - jumps and shock windows
   - relationship with wars and disasters
   - relationship with population
   - relationship with house-price variation
   - regional/country group differences

6. Use statistics:
   - descriptive statistics
   - rolling averages
   - rolling volatility
   - correlation and lagged correlation
   - Pearson and Spearman
   - Granger causality as optional extension
   - changepoint detection as optional extension
   - event-study windows
   - regression with controls

7. Use modelling:
   - baseline naive model
   - moving average
   - ARIMA/SARIMAX as optional extension
   - tree-based regression
   - classification model for price jump risk
   - scenario-based forecast

8. Produce outputs:
   - clean CSVs
   - DuckDB analytical database
   - dbt models
   - statistics tables
   - correlation tables
   - event-study outputs
   - model metrics
   - forecast outputs
   - HTML report/dashboard later

9. Explain the study clearly:
   - objective
   - data sources and limitations
   - methodology
   - equations
   - statistics used
   - interpretation of outputs
   - limitations and next steps

Important:

- Distinguish global commodity prices from local retail pump prices.
- Distinguish correlation from causality.
- Explain that war and disasters may affect fuel prices through supply, transport, sanctions, expectations, refining constraints, currency, and demand changes.
- Explain that house prices and fuel prices can co-move through inflation, interest rates, income, transport costs, and macroeconomic cycles, but are not necessarily directly causal.
- Keep the project suitable for GitHub, portfolio, interviews, and executive presentation.
