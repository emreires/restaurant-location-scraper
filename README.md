# la Madeleine Location & Review Assessment

This repository contains my implementation for the Web Data Technical Assessment.

## Objective
The project delivers four requirements:
1. Extract all U.S. la Madeleine locations from the WordPress endpoint.
2. Associate extracted locations with provided Google reviews.
3. Generate a single-slide insight deck.
4. Provide XPath and regex definitions for requested location-card fields.

## Project Structure
- `scripts/extract_locations.py`: endpoint extraction, normalization, and export.
- `scripts/associate_reviews.py`: review filtering, deterministic matching, and metrics.
- `scripts/generate_slide.py`: one-slide PPTX with scatter chart and key highlights.
- `docs/xpaths.md`: XPath + regex definitions.
- `Project Details/googleReview.csv`: provided review dataset.

## Environment Setup
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Planned Run Order
```powershell
python scripts/extract_locations.py
python scripts/associate_reviews.py
python scripts/generate_slide.py
```

## Deliverables
Generated outputs are written under `outputs/`.

## Notes
This README will be expanded in the final QA step with exact command examples and validation checks.
