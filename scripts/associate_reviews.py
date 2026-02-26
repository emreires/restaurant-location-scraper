"""Associate Google reviews with extracted la Madeleine locations."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

import pandas as pd


LOCATION_COLUMNS = [
    "locationName",
    "postalCode",
    "streetAddress",
    "streetAddress2",
    "fullAddress",
    "city",
    "state",
    "storeID",
]


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_text(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", clean_text(value).lower())


def normalize_phone(value: Any) -> str:
    return re.sub(r"[^0-9]+", "", clean_text(value))


def normalize_store_id(value: Any) -> str:
    raw = clean_text(value)
    if not raw:
        return ""
    try:
        return str(int(float(raw)))
    except ValueError:
        return raw


def extract_slug_from_website(website: str) -> str:
    match = re.search(r"/locations/([^/?#]+)", clean_text(website).lower())
    return clean_text(match.group(1)) if match else ""


def is_lamadeleine_review(website: str, name: str) -> bool:
    website_clean = clean_text(website).lower()
    name_clean = clean_text(name).lower()
    if "lamadeleine.com/locations/" in website_clean:
        return True
    return "la madeleine" in name_clean


def load_reviews(path: str) -> pd.DataFrame:
    reviews = pd.read_csv(path, dtype=str)

    reviews["reviewRating"] = pd.to_numeric(reviews.get("reviewRating"), errors="coerce")
    reviews["numberReviews"] = pd.to_numeric(reviews.get("numberReviews"), errors="coerce")
    reviews["overallRating"] = pd.to_numeric(reviews.get("overallRating"), errors="coerce")
    reviews["reviewDateParsed"] = pd.to_datetime(reviews.get("reviewDate"), errors="coerce", utc=True)

    reviews["website_norm"] = reviews.get("website", "").fillna("").map(clean_text)
    reviews["name_norm"] = reviews.get("name", "").fillna("").map(clean_text)
    reviews["fullAddress_norm"] = reviews.get("fullAddress", "").fillna("").map(normalize_text)
    reviews["phone_norm"] = reviews.get("phone", "").fillna("").map(normalize_phone)
    reviews["location_slug"] = reviews.get("website", "").fillna("").map(extract_slug_from_website)

    reviews["is_lamadeleine"] = reviews.apply(
        lambda row: is_lamadeleine_review(row.get("website", ""), row.get("name", "")),
        axis=1,
    )
    return reviews


def filter_lamadeleine_reviews(reviews: pd.DataFrame) -> pd.DataFrame:
    return reviews.loc[reviews["is_lamadeleine"]].copy()


def load_locations(path: str) -> pd.DataFrame:
    locations = pd.read_csv(path, dtype=str).fillna("")

    missing = [column for column in LOCATION_COLUMNS if column not in locations.columns]
    if missing:
        raise ValueError(f"Locations file is missing required columns: {missing}")

    locations = locations[LOCATION_COLUMNS].copy()
    locations["storeID"] = locations["storeID"].map(normalize_store_id)
    locations["fullAddress_norm"] = locations["fullAddress"].map(normalize_text)

    return locations


def load_location_lookup(raw_json_path: str) -> pd.DataFrame:
    try:
        with open(raw_json_path, "r", encoding="utf-8") as handle:
            records = json.load(handle)
    except FileNotFoundError:
        return pd.DataFrame(columns=["storeID", "slug", "phone_norm", "rawAddress_norm"])

    output: list[dict[str, str]] = []
    for record in records:
        acf = record.get("acf") if isinstance(record.get("acf"), dict) else {}
        hero = acf.get("locationHero") if isinstance(acf.get("locationHero"), dict) else {}

        store_id = normalize_store_id(hero.get("id") or record.get("id"))
        slug = clean_text(record.get("slug", "")).lower()

        address_1 = clean_text(hero.get("addressLine1"))
        address_2 = clean_text(hero.get("addressLine2"))
        city = clean_text(hero.get("city"))
        state = clean_text(hero.get("state"))
        postal_code = clean_text(hero.get("zip"))
        line_1 = ", ".join(value for value in [address_1, address_2] if value)
        line_2 = " ".join(value for value in [", ".join(v for v in [city, state] if v), postal_code] if value)
        full_address = ", ".join(value for value in [line_1, line_2] if value)

        output.append(
            {
                "storeID": store_id,
                "slug": slug,
                "phone_norm": normalize_phone(hero.get("phone")),
                "rawAddress_norm": normalize_text(full_address),
            }
        )

    return pd.DataFrame(output).drop_duplicates(subset=["storeID"])


def choose_stable_id(store_ids: list[str]) -> str:
    return sorted(store_ids, key=lambda value: (len(value), value))[0]


def build_match_indexes(locations: pd.DataFrame, lookup: pd.DataFrame) -> tuple[dict[str, str], dict[str, str], dict[str, str], pd.DataFrame]:
    enriched = locations.merge(lookup, on="storeID", how="left")

    slug_index_lists: dict[str, list[str]] = defaultdict(list)
    address_index_lists: dict[str, list[str]] = defaultdict(list)
    phone_index_lists: dict[str, list[str]] = defaultdict(list)

    for row in enriched.itertuples(index=False):
        store_id = clean_text(row.storeID)
        slug = clean_text(getattr(row, "slug", ""))
        address_norm = clean_text(row.fullAddress_norm)
        phone_norm = clean_text(getattr(row, "phone_norm", ""))

        if slug:
            slug_index_lists[slug].append(store_id)
        if address_norm:
            address_index_lists[address_norm].append(store_id)
        if phone_norm:
            phone_index_lists[phone_norm].append(store_id)

    slug_index = {key: choose_stable_id(values) for key, values in slug_index_lists.items()}
    address_index = {key: choose_stable_id(values) for key, values in address_index_lists.items()}
    phone_index = {key: choose_stable_id(values) for key, values in phone_index_lists.items()}

    return slug_index, address_index, phone_index, enriched


def match_reviews(
    reviews: pd.DataFrame,
    slug_index: dict[str, str],
    address_index: dict[str, str],
    phone_index: dict[str, str],
) -> pd.DataFrame:
    output = reviews.copy()

    matched_store_ids: list[str] = []
    methods: list[str] = []
    confidences: list[float] = []

    for row in output.itertuples(index=False):
        matched_store_id = ""
        match_method = "unmatched"
        confidence = 0.0

        slug = clean_text(getattr(row, "location_slug", "")).lower()
        if slug and slug in slug_index:
            matched_store_id = slug_index[slug]
            match_method = "website_slug"
            confidence = 1.0
        else:
            address_key = clean_text(getattr(row, "fullAddress_norm", ""))
            if address_key and address_key in address_index:
                matched_store_id = address_index[address_key]
                match_method = "address"
                confidence = 0.9
            else:
                phone_key = clean_text(getattr(row, "phone_norm", ""))
                if phone_key and phone_key in phone_index:
                    matched_store_id = phone_index[phone_key]
                    match_method = "phone"
                    confidence = 0.8

        matched_store_ids.append(matched_store_id)
        methods.append(match_method)
        confidences.append(confidence)

    output["matched_storeID"] = matched_store_ids
    output["match_method"] = methods
    output["match_confidence"] = confidences
    return output


def build_enriched_reviews(matched_reviews: pd.DataFrame, locations: pd.DataFrame) -> pd.DataFrame:
    location_ref = locations.copy().rename(
        columns={
            "storeID": "matched_storeID",
            "locationName": "matched_locationName",
            "postalCode": "matched_postalCode",
            "streetAddress": "matched_streetAddress",
            "streetAddress2": "matched_streetAddress2",
            "fullAddress": "matched_fullAddress",
            "city": "matched_city",
            "state": "matched_state",
        }
    )

    enriched = matched_reviews.merge(
        location_ref[
            [
                "matched_storeID",
                "matched_locationName",
                "matched_postalCode",
                "matched_streetAddress",
                "matched_streetAddress2",
                "matched_fullAddress",
                "matched_city",
                "matched_state",
            ]
        ],
        on="matched_storeID",
        how="left",
    )

    return enriched


def write_csv(frame: pd.DataFrame, path: str) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False, encoding="utf-8")
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reviews-csv", default="Project Details/googleReview.csv")
    parser.add_argument("--locations-csv", default="outputs/final/restaurant_locations.csv")
    parser.add_argument("--output-enriched", default="outputs/final/reviews_enriched.csv")
    parser.add_argument("--output-metrics", default="outputs/final/location_metrics.csv")
    parser.add_argument("--output-unmatched", default="outputs/final/unmatched_reviews.csv")
    parser.add_argument("--raw-json", default="outputs/raw/restaurant_locations_raw.json")
    parser.add_argument("--output-diagnostics", default="outputs/final/join_diagnostics.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    reviews = load_reviews(args.reviews_csv)
    lamadeleine_reviews = filter_lamadeleine_reviews(reviews)
    locations = load_locations(args.locations_csv)
    lookup = load_location_lookup(args.raw_json)

    slug_index, address_index, phone_index, _enriched_locations = build_match_indexes(locations, lookup)
    matched_reviews = match_reviews(lamadeleine_reviews, slug_index, address_index, phone_index)
    enriched_reviews = build_enriched_reviews(matched_reviews, locations)
    output_path = write_csv(enriched_reviews, args.output_enriched)

    summary = {
        "reviews_loaded": int(len(reviews)),
        "lamadeleine_reviews": int(len(lamadeleine_reviews)),
        "locations_loaded": int(len(locations)),
        "matched_reviews": int((matched_reviews["matched_storeID"] != "").sum()),
        "unmatched_reviews": int((matched_reviews["matched_storeID"] == "").sum()),
        "output_enriched": str(output_path),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
