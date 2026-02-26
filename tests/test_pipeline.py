import unittest
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import extract_locations  # noqa: E402
import associate_reviews  # noqa: E402


class TestExtraction(unittest.TestCase):
    def test_map_record_to_required_fields(self):
        record = {
            "id": 123,
            "title": {"rendered": "Fallback Name"},
            "acf": {
                "locationHero": {
                    "id": "35260",
                    "storeName": "Eastlake El Paso",
                    "addressLine1": "13395 W Gateway Blvd",
                    "addressLine2": "",
                    "city": "El Paso",
                    "state": "Texas",
                    "zip": "79928",
                }
            },
        }

        mapped = extract_locations.map_record_to_required_fields(record)

        self.assertEqual(mapped["locationName"], "Eastlake El Paso")
        self.assertEqual(mapped["state"], "TX")
        self.assertEqual(mapped["postalCode"], "79928")
        self.assertEqual(mapped["storeID"], "35260")
        self.assertTrue(mapped["fullAddress"].startswith("13395 W Gateway Blvd"))

    def test_validate_extracted_records_raises_on_blank_name(self):
        bad_records = [
            {
                "locationName": "",
                "postalCode": "12345",
                "streetAddress": "Main",
                "streetAddress2": "",
                "fullAddress": "Main, City, TX 12345",
                "city": "City",
                "state": "TX",
                "storeID": "1",
            }
        ]
        with self.assertRaises(ValueError):
            extract_locations.validate_extracted_records(bad_records)


class TestAssociation(unittest.TestCase):
    def test_match_priority_website_slug_over_address_and_phone(self):
        reviews = pd.DataFrame(
            [
                {
                    "location_slug": "test-location",
                    "fullAddress_norm": associate_reviews.normalize_text("123 Main St, Dallas, TX 75001"),
                    "phone_norm": associate_reviews.normalize_phone("214-555-0100"),
                }
            ]
        )

        slug_index = {"test-location": "100"}
        address_index = {associate_reviews.normalize_text("123 Main St, Dallas, TX 75001"): "200"}
        phone_index = {associate_reviews.normalize_phone("214-555-0100"): "300"}

        matched = associate_reviews.match_reviews(reviews, slug_index, address_index, phone_index)
        self.assertEqual(matched.iloc[0]["matched_storeID"], "100")
        self.assertEqual(matched.iloc[0]["match_method"], "website_slug")
        self.assertEqual(float(matched.iloc[0]["match_confidence"]), 1.0)

    def test_metrics_are_in_valid_range(self):
        frame = pd.DataFrame(
            [
                {
                    "matched_storeID": "1",
                    "matched_locationName": "A",
                    "matched_city": "Dallas",
                    "matched_state": "TX",
                    "reviewRating": 5,
                    "reviewDateParsed": pd.Timestamp("2024-01-01", tz="UTC"),
                },
                {
                    "matched_storeID": "1",
                    "matched_locationName": "A",
                    "matched_city": "Dallas",
                    "matched_state": "TX",
                    "reviewRating": 1,
                    "reviewDateParsed": pd.Timestamp("2024-01-02", tz="UTC"),
                },
            ]
        )

        metrics = associate_reviews.compute_location_metrics(frame)
        self.assertEqual(len(metrics), 1)
        avg = float(metrics.iloc[0]["avg_rating"])
        self.assertGreaterEqual(avg, 1.0)
        self.assertLessEqual(avg, 5.0)


if __name__ == "__main__":
    unittest.main()
