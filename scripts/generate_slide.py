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


def build_slide(title: str, plot_path: str, output_pptx: str) -> Path:
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

    for bullet in [
        "Scatter plot compares location volume and average rating.",
        "Use this slide as the discussion starting point for deeper review analysis.",
        "Automated insight bullets will be populated in the next iteration.",
    ]:
        p = insights_tf.add_paragraph()
        p.text = bullet
        p.level = 0
        p.font.size = Pt(14)

    presentation.save(output_path)
    return output_path


def main() -> None:
    args = parse_args()
    metrics = pd.read_csv(args.metrics_csv)
    _enriched = pd.read_csv(args.enriched_csv)

    plot_path = create_scatter_plot(metrics, args.plot_path)
    pptx_path = build_slide(args.title, str(plot_path), args.output_pptx)

    print(f"Created slide: {pptx_path}")


if __name__ == "__main__":
    main()
