# Age Layer Method

## Purpose

Build a cartography-ready Seoul building-age layer directly from the public age-bucket GeoJSON tiles already used in the earlier prototype.

## Why this method

The local Seoul footprint parquet is citywide and structurally useful, but it does not currently include a direct construction year field.

The public age-bucket tiles already expose the attributes needed for the first static map draft:

- `year`
- `address`
- `dongName`
- `dongCode`
- `h`

That makes the first production path straightforward:

1. download all Seoul-facing `z15` tiles for each age bucket
2. decompress and normalize the features
3. derive `approved_year`
4. assign a cartographic age band
5. write partitioned GeoParquet outputs

## Current bucket mapping

- `final-gz-2345` -> `pre_1960`
- `final-gz-678` -> `1960s` and `1970s` and `1980s`
- `final-gz-901` -> `1990s` and newer
- `final-buildings-null` -> `unknown`

The year string is stored as `YYYYMMDD` when present. The final age band is assigned from the first four digits.

## Output shape

The build script writes:

- one GeoParquet per source bucket in `data_processed/age_layers/`
- one summary JSON in `outputs/age_layer_summary.json`

This keeps the layer ready for static cartography work without forcing one large tracked binary into the repository.
