select
  f.year,
  f.series,
  f.avg_price,
  f.avg_mom_pct_change,
  f.avg_yoy_pct_change,
  f.monthly_volatility,
  f.jump_months,
  avg(c.population_total) as avg_population_total,
  sum(c.disaster_event_flag) as disaster_country_events,
  sum(c.conflict_event_flag) as conflict_country_events,
  avg(c.house_price_index) as avg_house_price_index
from {{ ref('mart_fuel_price_shocks') }} f
left join {{ ref('mart_country_macro_context') }} c using (year)
group by all
