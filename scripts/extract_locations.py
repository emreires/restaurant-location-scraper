"""Extract la Madeleine location data from WordPress JSON API."""

from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


DEFAULT_ENDPOINT = "https://lamadeleine.com/wp-json/wp/v2/restaurant-locations"
REQUIRED_COLUMNS = [
    "locationName",
    "postalCode",
    "streetAddress",
    "streetAddress2",
    "fullAddress",
    "city",
    "state",
    "storeID",
]

STATE_ABBR = {
    "ALABAMA": "AL", "ALASKA": "AK", "ARIZONA": "AZ", "ARKANSAS": "AR", "CALIFORNIA": "CA",
    "COLORADO": "CO", "CONNECTICUT": "CT", "DELAWARE": "DE", "FLORIDA": "FL", "GEORGIA": "GA",
    "HAWAII": "HI", "IDAHO": "ID", "ILLINOIS": "IL", "INDIANA": "IN", "IOWA": "IA",
    "KANSAS": "KS", "KENTUCKY": "KY", "LOUISIANA": "LA", "MAINE": "ME", "MARYLAND": "MD",
    "MASSACHUSETTS": "MA", "MICHIGAN": "MI", "MINNESOTA": "MN", "MISSISSIPPI": "MS", "MISSOURI": "MO",
    "MONTANA": "MT", "NEBRASKA": "NE", "NEVADA": "NV", "NEW HAMPSHIRE": "NH", "NEW JERSEY": "NJ",
    "NEW MEXICO": "NM", "NEW YORK": "NY", "NORTH CAROLINA": "NC", "NORTH DAKOTA": "ND", "OHIO": "OH",
    "OKLAHOMA": "OK", "OREGON": "OR", "PENNSYLVANIA": "PA", "RHODE ISLAND": "RI", "SOUTH CAROLINA": "SC",
    "SOUTH DAKOTA": "SD", "TENNESSEE": "TN", "TEXAS": "TX", "UTAH": "UT", "VERMONT": "VT",
    "VIRGINIA": "VA", "WASHINGTON": "WA", "WEST VIRGINIA": "WV", "WISCONSIN": "WI", "WYOMING": "WY",
    "DISTRICT OF COLUMBIA": "DC",
}
US_STATES = set(STATE_ABBR.values())


def build_session() -> requests.Session:
    """Create a requests session with conservative retry behavior."""
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def fetch_locations(endpoint: str, per_page: int, timeout: int) -> list[dict[str, Any]]:
    """Fetch all pages from the WordPress endpoint."""
    session = build_session()
    all_records: list[dict[str, Any]] = []
    page = 1
    total_pages = None

    while True:
        params = {"per_page": per_page, "page": page}
        response = session.get(endpoint, params=params, timeout=timeout)

        if response.status_code == 400 and "rest_post_invalid_page_number" in response.text:
            break

        response.raise_for_status()
        page_records = response.json()

        if not isinstance(page_records, list):
            raise ValueError("Unexpected API payload; expected a JSON array.")

        all_records.extend(page_records)

        if total_pages is None:
            header_value = response.headers.get("X-WP-TotalPages")
            total_pages = int(header_value) if header_value and header_value.isdigit() else None

        if total_pages is not None and page >= total_pages:
            break

        if len(page_records) < per_page:
            break

        page += 1

    return all_records


def write_raw_records(records: list[dict[str, Any]], raw_json_path: str) -> Path:
    path = Path(raw_json_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(records, handle, ensure_ascii=False, indent=2)
    return path


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = html.unescape(str(value))
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_state(state_value: str) -> str:
    state = clean_text(state_value).upper()
    if not state:
        return ""
    if len(state) == 2 and state.isalpha():
        return state
    return STATE_ABBR.get(state, state)


def build_full_address(street_1: str, street_2: str, city: str, state: str, postal_code: str) -> str:
    line_1 = ", ".join(part for part in [street_1, street_2] if part)
    line_2_parts = [part for part in [city, state, postal_code] if part]
    line_2 = ", ".join(line_2_parts[:-1])
    if line_2_parts:
        if line_2:
            line_2 = f"{line_2} {line_2_parts[-1]}"
        else:
            line_2 = line_2_parts[-1]
    return ", ".join(part for part in [line_1, line_2] if part)


def normalize_for_dedupe(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", clean_text(value).lower())


def map_record_to_required_fields(record: dict[str, Any]) -> dict[str, str]:
    acf = record.get("acf") if isinstance(record.get("acf"), dict) else {}
    hero = acf.get("locationHero") if isinstance(acf.get("locationHero"), dict) else {}

    location_name = clean_text(hero.get("storeName"))
    if not location_name:
        title_data = record.get("title") if isinstance(record.get("title"), dict) else {}
        location_name = clean_text(title_data.get("rendered"))

    street_1 = clean_text(hero.get("addressLine1"))
    street_2 = clean_text(hero.get("addressLine2"))
    city = clean_text(hero.get("city"))
    state = normalize_state(clean_text(hero.get("state")))
    postal_code = clean_text(hero.get("zip"))

    full_address = build_full_address(street_1, street_2, city, state, postal_code)

    store_id = clean_text(hero.get("id"))
    if not store_id:
        store_id = clean_text(record.get("id"))

    mapped = {
        "locationName": location_name,
        "postalCode": postal_code,
        "streetAddress": street_1,
        "streetAddress2": street_2,
        "fullAddress": full_address,
        "city": city,
        "state": state,
        "storeID": store_id,
    }
    return mapped


def map_records(records: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [map_record_to_required_fields(record) for record in records]


def filter_us_locations(records: list[dict[str, str]]) -> list[dict[str, str]]:
    return [record for record in records if record.get("state", "") in US_STATES]


def dedupe_locations(records: list[dict[str, str]]) -> list[dict[str, str]]:
    seen_store_ids: set[str] = set()
    seen_addresses: set[str] = set()
    deduped: list[dict[str, str]] = []

    for record in records:
        store_id = clean_text(record.get("storeID"))
        address_key = normalize_for_dedupe(record.get("fullAddress", ""))

        if store_id and store_id in seen_store_ids:
            continue
        if address_key and address_key in seen_addresses:
            continue

        deduped.append(record)

        if store_id:
            seen_store_ids.add(store_id)
        if address_key:
            seen_addresses.add(address_key)

    return deduped


def validate_extracted_records(records: list[dict[str, str]]) -> None:
    if not records:
        raise ValueError("Validation failed: no location records after filtering/deduplication.")

    for index, record in enumerate(records, start=1):
        missing_cols = [col for col in REQUIRED_COLUMNS if col not in record]
        if missing_cols:
            raise ValueError(f"Validation failed: missing columns {missing_cols} in record {index}.")

        if not clean_text(record.get("locationName")):
            raise ValueError(f"Validation failed: blank locationName in record {index}.")


def export_locations(records: list[dict[str, str]], output_csv: str, output_xlsx: str) -> tuple[Path, Path]:
    frame = pd.DataFrame(records)
    frame = frame.reindex(columns=REQUIRED_COLUMNS)

    csv_path = Path(output_csv)
    xlsx_path = Path(output_xlsx)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    xlsx_path.parent.mkdir(parents=True, exist_ok=True)

    frame.to_csv(csv_path, index=False, encoding="utf-8")
    frame.to_excel(xlsx_path, index=False)

    return csv_path, xlsx_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--per-page", type=int, default=100)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--output-csv", default="outputs/final/restaurant_locations.csv")
    parser.add_argument("--output-xlsx", default="outputs/final/restaurant_locations.xlsx")
    parser.add_argument("--raw-json", default="outputs/raw/restaurant_locations_raw.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records = fetch_locations(args.endpoint, args.per_page, args.timeout)
    raw_path = write_raw_records(records, args.raw_json)
    mapped_records = map_records(records)
    us_records = filter_us_locations(mapped_records)
    deduped_records = dedupe_locations(us_records)
    validate_extracted_records(deduped_records)
    csv_path, xlsx_path = export_locations(deduped_records, args.output_csv, args.output_xlsx)

    print(
        json.dumps(
            {
                "records_fetched": len(records),
                "mapped_records": len(mapped_records),
                "us_records": len(us_records),
                "deduped_records": len(deduped_records),
                "raw_json": str(raw_path),
                "output_csv": str(csv_path),
                "output_xlsx": str(xlsx_path),
                "validation": "passed",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
