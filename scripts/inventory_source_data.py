#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


DEFAULT_SOURCE = Path(
    "/data/omar/RESEARCH/change_detection/little_fan_project/data/raw/seoul_buildings_v2_4326.parquet"
)


def summarize_source(source_path: Path) -> dict:
    df = pd.read_parquet(source_path)

    district_counts = (
        df["sig_cd"].astype(str).value_counts().sort_index().to_dict()
        if "sig_cd" in df.columns
        else {}
    )

    null_counts = {
        column: int(df[column].isna().sum())
        for column in df.columns
        if column != "geometry"
    }

    sample_columns = [
        column
        for column in [
            "building_id",
            "building_name",
            "gro_flo_co",
            "und_flo_co",
            "sig_cd",
            "street_name",
            "house_number",
            "Shape__Area",
        ]
        if column in df.columns
    ]

    return {
        "source_path": str(source_path),
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "columns": [str(column) for column in df.columns],
        "district_count": int(df["sig_cd"].astype(str).nunique()) if "sig_cd" in df.columns else 0,
        "district_feature_counts": district_counts,
        "null_counts": null_counts,
        "sample_rows": df[sample_columns].head(5).fillna("").to_dict(orient="records"),
    }


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_path = DEFAULT_SOURCE

    if not source_path.exists():
        raise FileNotFoundError(
            f"Expected source parquet at {source_path}. Update DEFAULT_SOURCE or place the file there."
        )

    summary = summarize_source(source_path)
    output_path = repo_root / "outputs" / "source_inventory.json"
    output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
