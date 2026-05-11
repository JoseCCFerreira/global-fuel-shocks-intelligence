# Study Methodology

## Objective

The study analyses fuel-price variation and shock risk over time, then compares those patterns with wars, natural disasters, population and house-price variation.

## Core Measures

### Month-over-month change

```text
mom_pct_change = (price_t / price_t-1 - 1) * 100
```

This measures short-term fuel-price movement.

### Year-over-year change

```text
yoy_pct_change = (price_t / price_t-12 - 1) * 100
```

This controls for seasonality better than monthly change.

### Rolling volatility

```text
rolling_12m_volatility = std(mom_pct_change over last 12 months)
```

This measures instability, not direction.

### Jump detection

```text
zscore_mom = (mom_pct_change - mean(mom_pct_change)) / std(mom_pct_change)
price_jump_flag = abs(zscore_mom) >= 2.5
```

This marks unusually large price moves.

## Statistical Analysis

- Descriptive statistics: mean, max, volatility, jump count.
- Correlation: Pearson for linear relationships and Spearman for rank relationships.
- Lagged correlation: planned to study delayed event effects.
- Event study: compare price behaviour around war/disaster years.
- Regression: future phase to control for multiple drivers.

## Forecasting

The initial forecast uses a 12-month moving average as a transparent baseline. Future models can include ARIMA/SARIMAX, gradient boosting, random forests and regime-switching models.

## Interpretation Limits

Correlation does not prove causality. Wars and disasters may influence prices through supply disruption, sanctions, transport routes, refining capacity, market expectations and demand shocks, but each episode needs contextual validation.
