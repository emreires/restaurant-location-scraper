# la Madeleine Location & Review Assessment

This repository contains a full Python pipeline for the Web Data Technical Assessment.

## Assessment Coverage
The implementation covers all requested tasks:
1. Extract U.S. la Madeleine locations from `https://lamadeleine.com/wp-json/wp/v2/restaurant-locations`.
2. Associate provided Google reviews with extracted location records.
3. Generate a one-slide `.pptx` with chart + key insights.
4. Provide XPath + regex guidance for required on-page fields.

## Repository Layout
- `scripts/extract_locations.py`: endpoint ingestion, normalization, filtering, dedupe, validation, CSV/XLSX export.
- `scripts/associate_reviews.py`: review filtering, deterministic matching, enriched outputs, metrics, diagnostics.
- `scripts/generate_slide.py`: one-slide PPTX generator with scatter plot, labeled highlights, and automated insights.
- `docs/xpaths.md`: XPath + regex definitions for `locationName`, `hours`, `phoneNumber`, `distance`, latitude, longitude.
- `tests/test_pipeline.py`: unit tests for mapping, matching precedence, and metric sanity.
- `Project Details/googleReview.csv`: provided review dataset.

## Required Python Version
- Python `3.12` (tested with `3.12.10`)

## Setup
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## End-to-End Run
### 1) Extract locations
```powershell
python scripts/extract_locations.py
```

### 2) Associate reviews to locations
```powershell
python scripts/associate_reviews.py --reviews-csv "Project Details/googleReview.csv" --locations-csv "outputs/final/restaurant_locations.csv" --raw-json "outputs/raw/restaurant_locations_raw.json"
```

### 3) Generate single-slide insight deck
```powershell
python scripts/generate_slide.py --metrics-csv "outputs/final/location_metrics.csv" --enriched-csv "outputs/final/reviews_enriched.csv" --output-pptx "outputs/final/assessment_insights.pptx"
```

## Generated Outputs
- `outputs/raw/restaurant_locations_raw.json`
- `outputs/final/restaurant_locations.csv`
- `outputs/final/restaurant_locations.xlsx`
- `outputs/final/reviews_enriched.csv`
- `outputs/final/location_metrics.csv`
- `outputs/final/unmatched_reviews.csv`
- `outputs/final/join_diagnostics.json`
- `outputs/final/assessment_insights.pptx`
- `outputs/plots/review_scatter.png`

## Matching Strategy (Deterministic)
Review records are matched in this exact order:
1. `website slug` (highest confidence)
2. normalized `fullAddress`
3. normalized `phone`

Additional output fields include:
- `matched_storeID`
- `match_method`
- `match_confidence`

## Validation and Tests
Run unit tests:
```powershell
python -m unittest discover -s tests -p "test_*.py"
```

Validation checks in extraction include:
- non-empty output after filtering/deduplication
- required output schema presence
- non-blank `locationName`

## Notes
- Final location file uses exactly the required columns:
  - `locationName`
  - `postalCode`
  - `streetAddress`
  - `streetAddress2`
  - `fullAddress`
  - `city`
  - `state`
  - `storeID`
- The slide highlights and labels the same three locations used in the narrative:
  - top rated
  - lowest rated
  - highest volume

## Submission Checklist
- GitHub repository link with scripts and docs
- Location output file (`CSV` or `XLSX`)
- Single-slide presentation including visual + insights + XPath content reference
