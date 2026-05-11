select
  cast(date as date) as date,
  cast(month as date) as month,
  cast(year as integer) as year,
  series,
  cast(value as double) as value,
  cast(mom_pct_change as double) as mom_pct_change,
  cast(yoy_pct_change as double) as yoy_pct_change,
  cast(rolling_12m_avg as double) as rolling_12m_avg,
  cast(rolling_12m_volatility as double) as rolling_12m_volatility,
  cast(zscore_mom as double) as zscore_mom,
  cast(price_jump_flag as integer) as price_jump_flag
from raw_fuel_price_features
