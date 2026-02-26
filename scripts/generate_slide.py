"""Generate one-slide PPTX summary with scatter visualization."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from pptx import Presentation
from pptx.util import Inches, Pt


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metrics-csv", default="outputs/final/location_metrics.csv")
    parser.add_argument("--enriched-csv", default="outputs/final/reviews_enriched.csv")
    parser.add_argument("--output-pptx", default="outputs/final/assessment_insights.pptx")
    parser.add_argument("--title", default="la Madeleine Location Review Insights")
    parser.add_argument("--plot-path", default="outputs/plots/review_scatter.png")
    return parser.parse_args()


def create_scatter_plot(metrics: pd.DataFrame, plot_path: str) -> Path:
    output_path = Path(plot_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    metrics_plot = metrics.copy()
    metrics_plot["review_count"] = pd.to_numeric(metrics_plot["review_count"], errors="coerce")
    metrics_plot["avg_rating"] = pd.to_numeric(metrics_plot["avg_rating"], errors="coerce")
    metrics_plot = metrics_plot.dropna(subset=["review_count", "avg_rating"])

    fig, ax = plt.subplots(figsize=(7.5, 4.2), dpi=160)
    ax.scatter(
        metrics_plot["review_count"],
        metrics_plot["avg_rating"],
        s=45,
        alpha=0.75,
        color="#2468A2",
        edgecolor="white",
        linewidth=0.5,
    )
    ax.set_title("Location Review Volume vs. Average Rating", fontsize=11)
    ax.set_xlabel("Review Count", fontsize=10)
    ax.set_ylabel("Average Rating", fontsize=10)
    ax.grid(alpha=0.25, linestyle="--", linewidth=0.5)

    fig.tight_layout()
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)
    return output_path


def format_location_label(row: pd.Series) -> str:
    name = str(row.get("locationName", "Unknown")).strip()
    city = str(row.get("city", "")).strip()
    state = str(row.get("state", "")).strip()
    if city and state:
        return f"{name} ({city}, {state})"
    if city:
        return f"{name} ({city})"
    if state:
        return f"{name} ({state})"
    return name


def generate_insight_bullets(metrics: pd.DataFrame, enriched: pd.DataFrame) -> list[str]:
    if metrics.empty:
        return ["No matched location metrics were available for automated insights."]

    metrics_copy = metrics.copy()
    metrics_copy["review_count"] = pd.to_numeric(metrics_copy["review_count"], errors="coerce")
    metrics_copy["avg_rating"] = pd.to_numeric(metrics_copy["avg_rating"], errors="coerce")
    metrics_copy = metrics_copy.dropna(subset=["review_count", "avg_rating"])

    if metrics_copy.empty:
        return ["Metrics file did not contain numeric values for volume/rating analysis."]

    threshold = max(int(metrics_copy["review_count"].median()), 50)
    stable_subset = metrics_copy.loc[metrics_copy["review_count"] >= threshold]
    if stable_subset.empty:
        stable_subset = metrics_copy.copy()

    top_rated = stable_subset.sort_values(by=["avg_rating", "review_count"], ascending=[False, False]).iloc[0]
    bottom_rated = stable_subset.sort_values(by=["avg_rating", "review_count"], ascending=[True, False]).iloc[0]
    highest_volume = metrics_copy.sort_values(by=["review_count", "avg_rating"], ascending=[False, False]).iloc[0]

    matched_mask = enriched.get("matched_storeID", pd.Series(dtype=str)).fillna("") != ""
    matched_count = int(matched_mask.sum())
    total_count = int(len(enriched))
    coverage = (matched_count / total_count * 100) if total_count else 0.0

    rating_spread = float(stable_subset["avg_rating"].max() - stable_subset["avg_rating"].min())

    bullets = [
        (
            f"Top rated location (>= {threshold} reviews): {format_location_label(top_rated)} "
            f"with avg rating {float(top_rated['avg_rating']):.2f} across {int(top_rated['review_count'])} reviews."
        ),
        (
            f"Lowest rated location (>= {threshold} reviews): {format_location_label(bottom_rated)} "
            f"at {float(bottom_rated['avg_rating']):.2f}; indicates service quality variance."
        ),
        (
            f"Highest volume location: {format_location_label(highest_volume)} with "
            f"{int(highest_volume['review_count'])} reviews and avg rating {float(highest_volume['avg_rating']):.2f}."
        ),
        f"Review-to-location match coverage is {coverage:.1f}% ({matched_count}/{total_count}).",
        f"Rating spread across stable locations is {rating_spread:.2f} points, useful for geo-prioritized deep dives.",
    ]
    return bullets


def build_slide(title: str, plot_path: str, output_pptx: str, bullets: list[str]) -> Path:
    output_path = Path(output_pptx)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    presentation = Presentation()
    slide = presentation.slides.add_slide(presentation.slide_layouts[6])

    title_box = slide.shapes.add_textbox(Inches(0.4), Inches(0.2), Inches(12.4), Inches(0.7))
    title_tf = title_box.text_frame
    title_run = title_tf.paragraphs[0].add_run()
    title_run.text = title
    title_run.font.size = Pt(28)
    title_run.font.bold = True

    slide.shapes.add_picture(plot_path, Inches(0.5), Inches(1.0), width=Inches(7.4), height=Inches(4.6))

    insights_box = slide.shapes.add_textbox(Inches(8.1), Inches(1.0), Inches(5.0), Inches(4.6))
    insights_tf = insights_box.text_frame
    insights_tf.word_wrap = True

    p0 = insights_tf.paragraphs[0]
    p0.text = "Key Highlights"
    p0.font.size = Pt(20)
    p0.font.bold = True

    for bullet in bullets:
        p = insights_tf.add_paragraph()
        p.text = bullet
        p.level = 0
        p.font.size = Pt(12)

    presentation.save(output_path)
    return output_path


def main() -> None:
    args = parse_args()
    metrics = pd.read_csv(args.metrics_csv)
    enriched = pd.read_csv(args.enriched_csv)

    plot_path = create_scatter_plot(metrics, args.plot_path)
    bullets = generate_insight_bullets(metrics, enriched)
    pptx_path = build_slide(args.title, str(plot_path), args.output_pptx, bullets)

    print(f"Created slide: {pptx_path}")


if __name__ == "__main__":
    main()
