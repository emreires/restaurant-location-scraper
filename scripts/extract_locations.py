"""Extract la Madeleine location data from WordPress JSON API."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


DEFAULT_ENDPOINT = "https://lamadeleine.com/wp-json/wp/v2/restaurant-locations"


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
    print(json.dumps({"records_fetched": len(records), "raw_json": str(raw_path)}, indent=2))


if __name__ == "__main__":
    main()
