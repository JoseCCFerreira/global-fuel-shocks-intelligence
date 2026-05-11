from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

import pandas as pd
import requests


ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
REF = ROOT / "data" / "reference"


PINK_SHEET_URLS = [
    "https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/related/CMO-Historical-Data-Monthly.xlsx",
    "https://thedocs.worldbank.org/en/doc/5d903e848db1d1b83e0ec8f744e55570-0350012021/related/CMO-Historical-Data-Monthly.xlsx",
    "https://pubdocs.worldbank.org/en/561011486076393416/CMO-Historical-Data-Monthly.xlsx",
]

OWID_DISASTER_URL = "https://ourworldindata.org/grapher/economic-damage-from-natural-disasters.csv?v=1&csvType=full&useColumnShortNames=false"
OWID_WAR_URL = "https://ourworldindata.org/grapher/deaths-in-armed-conflicts-by-country.csv?download-format=tabular"
HOUSE_PRICE_URL = "https://datahub.io/core/house-prices-global/_r/-/archive/WS_SPP_csv_col.csv"

WB_INDICATORS = {
    "SP.POP.TOTL": "population_total",
    "EP.PMP.SGAS.CD": "gasoline_pump_price_usd_liter",
    "EP.PMP.DESL.CD": "diesel_pump_price_usd_liter",
}


def get(url: str) -> requests.Response:
    response = requests.get(url, timeout=60, verify=False)
    response.raise_for_status()
    return response


def download_file(url: str, path: Path) -> bool:
    try:
        response = get(url)
        path.write_bytes(response.content)
        return True
    except Exception as exc:
        print(f"Could not download {url}: {exc}")
        return False


def fetch_world_bank_indicator(indicator: str, name: str) -> None:
    rows = []
    page = 1
    while True:
        url = f"https://api.worldbank.org/v2/country/all/indicator/{indicator}?format=json&per_page=20000&page={page}"
        payload = get(url).json()
        if not isinstance(payload, list) or len(payload) < 2:
            break
        meta, data = payload
        rows.extend(data)
        if page >= int(meta.get("pages", 1)):
            break
        page += 1
    normalized = []
    for item in rows:
        if item.get("value") is None:
            continue
        normalized.append(
            {
                "country_code": item["countryiso3code"],
                "country": item["country"]["value"],
                "year": int(item["date"]),
                "indicator_code": indicator,
                "indicator_name": name,
                "value": item["value"],
            }
        )
    pd.DataFrame(normalized).to_csv(RAW / f"world_bank_{name}.csv", index=False)


def create_source_registry() -> None:
    sources = [
        {
            "source": "World Bank Commodity Markets Pink Sheet",
            "url": PINK_SHEET_URLS[0],
            "coverage": "Monthly commodity prices, usually from 1960 onward depending on series.",
            "use": "Global crude oil, natural gas and energy commodity price tracking.",
        },
        {
            "source": "World Bank Indicators API",
            "url": "https://api.worldbank.org/v2/",
            "coverage": "Annual country-level indicators.",
            "use": "Population, gasoline pump prices and diesel pump prices when available.",
        },
        {
            "source": "Our World in Data / EM-DAT",
            "url": OWID_DISASTER_URL,
            "coverage": "Natural disaster damage by country/year where available.",
            "use": "Event severity proxy for catastrophe correlation and event windows.",
        },
        {
            "source": "Our World in Data / UCDP",
            "url": OWID_WAR_URL,
            "coverage": "Armed conflict deaths by country/year where available.",
            "use": "War/conflict severity proxy.",
        },
        {
            "source": "BIS/DataHub residential property prices",
            "url": HOUSE_PRICE_URL,
            "coverage": "Residential property price indexes for selected countries.",
            "use": "House-price variation comparison.",
        },
    ]
    pd.DataFrame(sources).to_csv(REF / "source_registry.csv", index=False)


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    REF.mkdir(parents=True, exist_ok=True)
    create_source_registry()

    pink_path = RAW / "world_bank_pink_sheet_monthly.xlsx"
    for url in PINK_SHEET_URLS:
        if download_file(url, pink_path):
            break

    download_file(OWID_DISASTER_URL, RAW / "owid_disaster_damage.csv")
    download_file(OWID_WAR_URL, RAW / "owid_conflict_deaths.csv")
    download_file(HOUSE_PRICE_URL, RAW / "house_prices_global.csv")

    for indicator, name in WB_INDICATORS.items():
        try:
            fetch_world_bank_indicator(indicator, name)
        except Exception as exc:
            print(f"World Bank indicator failed {indicator}: {exc}")

    metadata = {
        "raw_files": sorted(path.name for path in RAW.glob("*")),
        "sources": sorted(path.name for path in REF.glob("*")),
    }
    (REF / "fetch_manifest.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
