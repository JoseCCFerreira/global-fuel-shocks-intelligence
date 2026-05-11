select
  *,
  case
    when abs(zscore_mom) >= 3 then 'extreme_jump'
    when abs(zscore_mom) >= 2.5 then 'jump'
    when abs(zscore_mom) >= 1.5 then 'elevated'
    else 'normal'
  end as shock_band,
  lag(value, 1) over (partition by series order by month) as previous_price,
  lead(value, 1) over (partition by series order by month) as next_price
from {{ ref('stg_fuel_price_features') }}
