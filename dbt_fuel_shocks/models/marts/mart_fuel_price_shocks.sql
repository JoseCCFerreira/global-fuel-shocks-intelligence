select
  year,
  series,
  count(*) as observations,
  avg(value) as avg_price,
  avg(mom_pct_change) as avg_mom_pct_change,
  avg(yoy_pct_change) as avg_yoy_pct_change,
  stddev_samp(mom_pct_change) as monthly_volatility,
  sum(price_jump_flag) as jump_months,
  max(abs(zscore_mom)) as max_abs_zscore
from {{ ref('int_fuel_shock_features') }}
group by all
