select *
from {{ ref('stg_fuel_price_features') }}
where value < 0
   or year < 1800
   or year > 2100
