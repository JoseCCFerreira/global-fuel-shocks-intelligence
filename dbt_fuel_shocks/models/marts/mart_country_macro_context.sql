select
  country,
  year,
  population_total,
  gasoline_pump_price_usd_liter,
  diesel_pump_price_usd_liter,
  disaster_damage_usd,
  conflict_deaths,
  house_price_index,
  disaster_event_flag,
  conflict_event_flag
from {{ ref('int_country_event_context') }}
