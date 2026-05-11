select
  country,
  year,
  population_total,
  gasoline_pump_price_usd_liter,
  diesel_pump_price_usd_liter,
  disaster_damage_usd,
  conflict_deaths,
  house_price_index,
  case when disaster_damage_usd > 0 then 1 else 0 end as disaster_event_flag,
  case when conflict_deaths > 0 then 1 else 0 end as conflict_event_flag
from {{ ref('stg_country_context') }}
