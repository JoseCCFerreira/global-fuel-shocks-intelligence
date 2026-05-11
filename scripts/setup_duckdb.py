from __future__ import annotations

from pathlib import Path

import duckdb


ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "data" / "outputs"
DB_PATH = PROCESSED / "fuel_shocks.duckdb"


def create_table(conn: duckdb.DuckDBPyConnection, name: str, csv_name: str) -> None:
    path = PROCESSED / csv_name
    conn.execute(f"DROP TABLE IF EXISTS {name}")
    if path.exists():
        conn.execute(f"CREATE TABLE {name} AS SELECT * FROM read_csv_auto('{path.as_posix()}', header=true)")
    else:
        conn.execute(f"CREATE TABLE {name} AS SELECT 1 AS missing WHERE false")


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(DB_PATH))
    create_table(conn, "raw_fuel_prices_long", "fuel_prices_long.csv")
    create_table(conn, "raw_fuel_price_features", "fuel_price_features.csv")
    create_table(conn, "raw_world_bank_indicators", "world_bank_indicators.csv")
    create_table(conn, "raw_disaster_damage", "disaster_damage.csv")
    create_table(conn, "raw_conflict_deaths", "conflict_deaths.csv")
    create_table(conn, "raw_house_prices", "house_prices.csv")
    create_table(conn, "raw_country_geo_reference", "country_geo_reference.csv")
    create_table(conn, "raw_fuel_yearly_features", "fuel_yearly_features.csv")

    conn.execute("DROP VIEW IF EXISTS mart_global_fuel_shocks")
    conn.execute(
        """
        CREATE VIEW mart_global_fuel_shocks AS
        SELECT
          year,
          series,
          fuel_price_avg,
          fuel_yoy_avg,
          fuel_volatility,
          jump_count
        FROM raw_fuel_yearly_features
        """
    )
    conn.execute("DROP VIEW IF EXISTS mart_country_context")
    conn.execute(
        """
        CREATE VIEW mart_country_context AS
        WITH p AS (
          SELECT country, country_code, cast(year AS integer) AS year, indicator_name, value
          FROM raw_world_bank_indicators
        ),
        d AS (
          SELECT country, country_code, cast(year AS integer) AS year, disaster_damage_usd
          FROM raw_disaster_damage
        ),
        c AS (
          SELECT country, country_code, cast(year AS integer) AS year, conflict_deaths
          FROM raw_conflict_deaths
        ),
        h AS (
          SELECT country, cast(year AS integer) AS year, house_price_index
          FROM raw_house_prices
        )
        SELECT
          coalesce(p.country, d.country, c.country, h.country) AS country,
          coalesce(
            max(nullif(p.country_code, '')),
            max(nullif(d.country_code, '')),
            max(case when length(c.country_code) = 3 and c.country_code not like 'OWID_%' then c.country_code end)
          ) AS source_country_code,
          coalesce(p.year, d.year, c.year, h.year) AS year,
          max(case when p.indicator_name = 'population_total' then p.value end) AS population_total,
          max(case when p.indicator_name = 'gasoline_pump_price_usd_liter' then p.value end) AS gasoline_pump_price_usd_liter,
          max(case when p.indicator_name = 'diesel_pump_price_usd_liter' then p.value end) AS diesel_pump_price_usd_liter,
          max(d.disaster_damage_usd) AS disaster_damage_usd,
          max(c.conflict_deaths) AS conflict_deaths,
          max(h.house_price_index) AS house_price_index
        FROM p
        FULL OUTER JOIN d USING (country, year)
        FULL OUTER JOIN c USING (country, year)
        FULL OUTER JOIN h USING (country, year)
        GROUP BY 1,3
        """
    )
    conn.execute("DROP VIEW IF EXISTS mart_country_geo_context")
    conn.execute(
        """
        CREATE VIEW mart_country_geo_context AS
        SELECT
          c.*,
          coalesce(c.source_country_code, g.country_code) AS country_code,
          g.continent,
          c.gasoline_pump_price_usd_liter - lag(c.gasoline_pump_price_usd_liter) over (partition by c.country order by c.year) as gasoline_price_abs_change,
          (c.gasoline_pump_price_usd_liter / nullif(lag(c.gasoline_pump_price_usd_liter) over (partition by c.country order by c.year), 0) - 1) * 100 as gasoline_price_pct_change,
          c.diesel_pump_price_usd_liter - lag(c.diesel_pump_price_usd_liter) over (partition by c.country order by c.year) as diesel_price_abs_change,
          (c.diesel_pump_price_usd_liter / nullif(lag(c.diesel_pump_price_usd_liter) over (partition by c.country order by c.year), 0) - 1) * 100 as diesel_price_pct_change,
          c.population_total - lag(c.population_total) over (partition by c.country order by c.year) as population_abs_change,
          (c.population_total / nullif(lag(c.population_total) over (partition by c.country order by c.year), 0) - 1) * 100 as population_pct_change
        FROM mart_country_context c
        LEFT JOIN raw_country_geo_reference g USING (country)
        """
    )
    conn.close()
    print(f"DuckDB database created: {DB_PATH}")


if __name__ == "__main__":
    main()
