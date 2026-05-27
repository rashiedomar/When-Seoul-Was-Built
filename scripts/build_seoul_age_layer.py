#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import shape


SEOUL_BOUNDS = {
    "min_lon": 126.76,
    "min_lat": 37.43,
    "max_lon": 127.19,
    "max_lat": 37.70,
}

TILE_ZOOM = 15
MAX_WORKERS = 12
REQUEST_TIMEOUT = 30
RETRIES = 3
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"

BUCKETS = [
    {"id": "pre_1960", "source_key": "final-gz-2345"},
    {"id": "mid_century", "source_key": "final-gz-678"},
    {"id": "modern", "source_key": "final-gz-901"},
    {"id": "unknown", "source_key": "final-buildings-null"},
]


def lonlat_to_tile(lon: float, lat: float, z: int) -> tuple[int, int]:
    n = 2**z
    x = int((lon + 180.0) / 360.0 * n)
    lat_rad = math.radians(lat)
    y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return x, y


def iter_tiles(bounds: dict[str, float], z: int) -> list[tuple[int, int]]:
    min_x, max_y = lonlat_to_tile(bounds["min_lon"], bounds["min_lat"], z)
    max_x, min_y = lonlat_to_tile(bounds["max_lon"], bounds["max_lat"], z)
    return [(x, y) for x in range(min_x, max_x + 1) for y in range(min_y, max_y + 1)]


def normalize_year(year_value: object) -> tuple[str | None, int | None]:
    if year_value in (None, "", 0):
        return None, None
    year_raw = str(year_value)
    if len(year_raw) != 8 or not year_raw.isdigit():
        return year_raw, None
    approved_year = int(year_raw[:4])
    if approved_year < 1800 or approved_year > 2026:
        return year_raw, None
    return year_raw, approved_year


def assign_age_band(approved_year: int | None) -> str:
    if approved_year is None:
        return "unknown"
    if approved_year <= 1959:
        return "pre_1960"
    if approved_year <= 1969:
        return "y1960s"
    if approved_year <= 1979:
        return "y1970s"
    if approved_year <= 1989:
        return "y1980s"
    if approved_year <= 1999:
        return "y1990s"
    if approved_year <= 2009:
        return "y2000s"
    return "y2010_plus"


def fetch_tile(source_key: str, z: int, x: int, y: int) -> list[dict]:
    url = f"https://s3.amazonaws.com/odd-tiles/{source_key}/{z}/{x}/{y}.geojson"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    last_error: Exception | None = None
    for attempt in range(1, RETRIES + 1):
        try:
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
                raw = response.read()
            if source_key != "final-buildings-null":
                raw = gzip.decompress(raw)
            payload = json.loads(raw.decode("utf-8"))
            return payload.get("features", [])
        except urllib.error.HTTPError as exc:
            if exc.code in (403, 404):
                return []
            last_error = exc
            if attempt == RETRIES:
                raise
            time.sleep(0.5 * attempt)
        except Exception as exc:  # pragma: no cover - network behavior
            last_error = exc
            if attempt == RETRIES:
                raise
            time.sleep(0.5 * attempt)
    raise RuntimeError(f"Failed to fetch {url}: {last_error}")


def feature_to_row(feature: dict, source_key: str, tile_z: int, tile_x: int, tile_y: int) -> dict:
    props = feature.get("properties", {})
    geom = shape(feature["geometry"])
    year_raw, approved_year = normalize_year(props.get("year"))
    feature_hash = hashlib.sha1(
        geom.wkb + json.dumps(props, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return {
        "feature_hash": feature_hash,
        "source_key": source_key,
        "tile_z": tile_z,
        "tile_x": tile_x,
        "tile_y": tile_y,
        "approved_date_raw": year_raw,
        "approved_year": approved_year,
        "age_band": assign_age_band(approved_year),
        "height_m": float(props.get("h") or 0.0),
        "address": props.get("address"),
        "dong_name": props.get("dongName"),
        "dong_code": str(props.get("dongCode")) if props.get("dongCode") is not None else None,
        "geometry": geom,
    }


def collect_bucket(source_key: str, tiles: list[tuple[int, int]]) -> tuple[gpd.GeoDataFrame, dict]:
    rows: list[dict] = []
    failed_tiles: list[dict] = []
    fetched_tiles = 0
    raw_feature_count = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_map = {
            executor.submit(fetch_tile, source_key, TILE_ZOOM, x, y): (x, y)
            for x, y in tiles
        }
        for future in as_completed(future_map):
            x, y = future_map[future]
            try:
                features = future.result()
            except Exception as exc:
                failed_tiles.append({"x": x, "y": y, "error": str(exc)})
                continue

            fetched_tiles += 1
            raw_feature_count += len(features)
            for feature in features:
                rows.append(feature_to_row(feature, source_key, TILE_ZOOM, x, y))

    if rows:
        frame = gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")
        frame = frame.drop_duplicates(subset=["feature_hash"]).reset_index(drop=True)
        frame["approved_year"] = frame["approved_year"].astype("Int64")
    else:
        frame = gpd.GeoDataFrame(
            columns=[
                "feature_hash",
                "source_key",
                "tile_z",
                "tile_x",
                "tile_y",
                "approved_date_raw",
                "approved_year",
                "age_band",
                "height_m",
                "address",
                "dong_name",
                "dong_code",
                "geometry",
            ],
            geometry="geometry",
            crs="EPSG:4326",
        )

    summary = {
        "source_key": source_key,
        "tile_zoom": TILE_ZOOM,
        "tile_count_requested": len(tiles),
        "tile_count_fetched": fetched_tiles,
        "tile_count_failed": len(failed_tiles),
        "raw_feature_count": raw_feature_count,
        "deduped_feature_count": int(len(frame)),
        "failed_tiles": failed_tiles[:50],
        "age_band_counts": {
            str(key): int(value)
            for key, value in frame["age_band"].value_counts(dropna=False).sort_index().items()
        }
        if len(frame)
        else {},
        "approved_year_min": int(frame["approved_year"].dropna().min()) if frame["approved_year"].notna().any() else None,
        "approved_year_max": int(frame["approved_year"].dropna().max()) if frame["approved_year"].notna().any() else None,
    }

    return frame, summary


def build_age_layers(repo_root: Path) -> dict:
    tiles = iter_tiles(SEOUL_BOUNDS, TILE_ZOOM)
    processed_dir = repo_root / "data_processed" / "age_layers"
    processed_dir.mkdir(parents=True, exist_ok=True)

    bucket_summaries = []
    total_features = 0

    for bucket in BUCKETS:
        source_key = bucket["source_key"]
        print(f"[build] {source_key} over {len(tiles)} tiles")
        frame, summary = collect_bucket(source_key, tiles)
        output_path = processed_dir / f"{source_key}.parquet"
        frame.to_parquet(output_path, index=False)
        total_features += len(frame)
        summary["output_path"] = str(output_path.relative_to(repo_root))
        bucket_summaries.append(summary)
        print(
            f"[done] {source_key}: {summary['deduped_feature_count']} features, "
            f"{summary['tile_count_failed']} failed tiles"
        )

    result = {
        "title": "When Seoul Was Built",
        "tile_zoom": TILE_ZOOM,
        "bounds": SEOUL_BOUNDS,
        "tile_count_total": len(tiles),
        "bucket_count": len(BUCKETS),
        "total_feature_count": int(total_features),
        "outputs": bucket_summaries,
    }

    summary_path = repo_root / "outputs" / "age_layer_summary.json"
    summary_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[summary] wrote {summary_path}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a Seoul building-age layer from public tile groups.")
    parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    build_age_layers(repo_root)


if __name__ == "__main__":
    main()
