"""Associate Google reviews with extracted la Madeleine locations."""

from __future__ import annotations

import argparse
import json
import re
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
    locations["fullAddress_norm"] = locations["fullAddress"].map(normalize_text)

    return locations


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

    summary = {
        "reviews_loaded": int(len(reviews)),
        "lamadeleine_reviews": int(len(lamadeleine_reviews)),
        "locations_loaded": int(len(locations)),
        "review_date_min": str(lamadeleine_reviews["reviewDateParsed"].min()),
        "review_date_max": str(lamadeleine_reviews["reviewDateParsed"].max()),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
