select
  country,
  cast(year as integer) as year,
  cast(population_total as double) as population_total,
  cast(gasoline_pump_price_usd_liter as double) as gasoline_pump_price_usd_liter,
  cast(diesel_pump_price_usd_liter as double) as diesel_pump_price_usd_liter,
  cast(disaster_damage_usd as double) as disaster_damage_usd,
  cast(conflict_deaths as double) as conflict_deaths,
  cast(house_price_index as double) as house_price_index,
  country_code,
  continent,
  cast(gasoline_price_abs_change as double) as gasoline_price_abs_change,
  cast(gasoline_price_pct_change as double) as gasoline_price_pct_change,
  cast(diesel_price_abs_change as double) as diesel_price_abs_change,
  cast(diesel_price_pct_change as double) as diesel_price_pct_change,
  cast(population_abs_change as double) as population_abs_change,
  cast(population_pct_change as double) as population_pct_change
from mart_country_geo_context
