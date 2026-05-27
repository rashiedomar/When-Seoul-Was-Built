#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import base64

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import pandas as pd
from PIL import Image
from matplotlib.patches import Patch


FIGURE_TITLE = "When Seoul Was Built"
FIGURE_SUBTITLE = "A fun static map of Seoul's building approval eras assembled from public age-tile geometry"
FIGURE_FOOTNOTE = (
    "Source age tiles were normalized into a citywide layer. "
    "Invalid or missing approval dates are grouped as Unknown."
)

BACKGROUND = "#0d0a08"
TEXT_PRIMARY = "#eadfbe"
TEXT_MUTED = "#c3b28c"
FRAME_COLOR = "#3a3126"
FABRIC_COLOR = "#1a1510"

BAND_ORDER = [
    "unknown",
    "pre_1960",
    "y1960s",
    "y1970s",
    "y1980s",
    "y1990s",
    "y2000s",
    "y2010_plus",
]

BAND_LABELS = {
    "pre_1960": "Before 1960",
    "y1960s": "1960-1969",
    "y1970s": "1970-1979",
    "y1980s": "1980-1989",
    "y1990s": "1990-1999",
    "y2000s": "2000-2009",
    "y2010_plus": "2010-2016",
    "unknown": "Unknown",
}

BAND_COLORS = {
    "pre_1960": "#b86d31",
    "y1960s": "#cf8435",
    "y1970s": "#dba04a",
    "y1980s": "#e6c56e",
    "y1990s": "#7fc8ca",
    "y2000s": "#4f8fd7",
    "y2010_plus": "#294b97",
    "unknown": "#8a8fa5",
}

SOURCE_FILES = [
    "final-gz-2345.parquet",
    "final-gz-678.parquet",
    "final-gz-901.parquet",
    "final-buildings-null.parquet",
]


def format_count(value: int) -> str:
    return f"{value:,}"


def load_counts(summary_path: Path) -> dict[str, int]:
    import json

    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    counts = {band: 0 for band in BAND_ORDER}
    for bucket in payload["outputs"]:
        for band, value in bucket["age_band_counts"].items():
            counts[band] = counts.get(band, 0) + int(value)
    return counts


def render_map(repo_root: Path) -> Path:
    layers_dir = repo_root / "data_processed" / "age_layers"
    outputs_dir = repo_root / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)

    counts = load_counts(outputs_dir / "age_layer_summary.json")

    fig = plt.figure(figsize=(11.5, 14.8), facecolor=BACKGROUND)
    ax = fig.add_axes([0.02, 0.085, 0.96, 0.83])
    ax.set_facecolor(BACKGROUND)

    layer_frames = {}
    minx = miny = None
    maxx = maxy = None

    for file_name in SOURCE_FILES:
        gdf = gpd.read_parquet(layers_dir / file_name, columns=["age_band", "geometry"])
        gdf = gdf.to_crs(5179)
        layer_frames[file_name] = gdf

        bounds = gdf.total_bounds
        minx = bounds[0] if minx is None else min(minx, bounds[0])
        miny = bounds[1] if miny is None else min(miny, bounds[1])
        maxx = bounds[2] if maxx is None else max(maxx, bounds[2])
        maxy = bounds[3] if maxy is None else max(maxy, bounds[3])

    base_fabric = gpd.GeoDataFrame(
        geometry=pd.concat([frame.geometry for frame in layer_frames.values()], ignore_index=True),
        crs="EPSG:5179",
    )
    base_fabric.plot(ax=ax, color=FABRIC_COLOR, linewidth=0, edgecolor="none", alpha=1.0)

    for band in BAND_ORDER:
        band_frames = [frame.loc[frame["age_band"] == band, ["geometry"]] for frame in layer_frames.values()]
        band_frame = pd.concat(band_frames, ignore_index=True)
        if band_frame.empty:
            continue
        band_gdf = gpd.GeoDataFrame(band_frame, geometry="geometry", crs="EPSG:5179")
        alpha = 0.72 if band == "unknown" else 0.93
        band_gdf.plot(
            ax=ax,
            color=BAND_COLORS[band],
            linewidth=0,
            edgecolor="none",
            alpha=alpha,
        )

    pad_x = (maxx - minx) * 0.03
    pad_y = (maxy - miny) * 0.035
    ax.set_xlim(minx - pad_x, maxx + pad_x)
    ax.set_ylim(miny - pad_y, maxy + pad_y)
    ax.set_aspect("equal")
    ax.axis("off")

    fig.text(0.035, 0.964, FIGURE_TITLE, color=TEXT_PRIMARY, fontsize=27, fontweight="bold")
    fig.text(0.035, 0.942, FIGURE_SUBTITLE, color=TEXT_MUTED, fontsize=11.5)
    fig.text(
        0.035,
        0.924,
        f"Deduped buildings in mapped layer: {format_count(sum(counts.values()))}",
        color=TEXT_MUTED,
        fontsize=10.5,
    )

    legend_handles = [
        Patch(facecolor=BAND_COLORS[band], edgecolor="none", label=f"{BAND_LABELS[band]}  ({format_count(counts[band])})")
        for band in BAND_ORDER
    ]
    legend = fig.legend(
        handles=legend_handles,
        loc="lower left",
        bbox_to_anchor=(0.035, 0.062),
        frameon=True,
        framealpha=0.94,
        facecolor=BACKGROUND,
        edgecolor=FRAME_COLOR,
        fontsize=9.5,
        labelspacing=0.55,
        borderpad=0.8,
    )
    for text in legend.get_texts():
        text.set_color(TEXT_PRIMARY)

    fig.text(0.035, 0.026, FIGURE_FOOTNOTE, color=TEXT_MUTED, fontsize=9)

    png_path = outputs_dir / "when-seoul-was-built.png"
    preview_svg_path = outputs_dir / "when-seoul-was-built-preview.svg"
    pdf_path = outputs_dir / "when-seoul-was-built.pdf"
    fig.savefig(png_path, dpi=300, facecolor=BACKGROUND, bbox_inches="tight", pad_inches=0.18)
    fig.savefig(pdf_path, facecolor=BACKGROUND, bbox_inches="tight", pad_inches=0.18)
    plt.close(fig)

    with Image.open(png_path) as image:
        preview_width = 900
        preview_height = round(image.height * (preview_width / image.width))
        preview_image = image.convert("RGB").resize(
            (preview_width, preview_height),
            Image.Resampling.LANCZOS,
        )
        jpeg_path = outputs_dir / "when-seoul-was-built-preview.jpg"
        preview_image.save(jpeg_path, format="JPEG", quality=72, optimize=True)

    preview_image = mpimg.imread(jpeg_path)
    height_px, width_px = preview_image.shape[:2]
    jpeg_base64 = base64.b64encode(jpeg_path.read_bytes()).decode("ascii")
    svg_text = (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {width_px} {height_px}">'
        f'<image width="{width_px}" height="{height_px}" xlink:href="data:image/jpeg;base64,{jpeg_base64}"/>'
        "</svg>"
    )
    preview_svg_path.write_text(svg_text, encoding="utf-8")
    jpeg_path.unlink(missing_ok=True)
    return preview_svg_path


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    output_path = render_map(repo_root)
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
