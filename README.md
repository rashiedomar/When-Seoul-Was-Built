# When Seoul Was Built

<p align="center">
  <img src="outputs/when-seoul-was-built-preview.svg" alt="When Seoul Was Built" width="420">
</p>

`When Seoul Was Built` is a fun project that turns Seoul's building approval records into a dense static map of urban age.

Instead of focusing on interaction, the project focuses on one final image:

- a citywide building-age map
- clear era bins
- a dark cartographic style
- reproducible data processing and export steps

## Project idea

The question is simple:

`What does Seoul look like if every building is colored by when it was approved?`

The output is a static figure built from public Seoul age-tile geometry, cleaned and normalized into a single renderable layer.

## Current output

Main generated figure:

- [outputs/when-seoul-was-built-preview.svg](outputs/when-seoul-was-built-preview.svg)

Supporting summary:

- [outputs/age_layer_summary.json](outputs/age_layer_summary.json)
- [outputs/source_inventory.json](outputs/source_inventory.json)

## Data used

This repository currently works from two practical inputs:

1. a local Seoul building footprint parquet used for source inventory and structural context
2. public Seoul building-age tile groups that provide the approval-era geometry used for the final map

Age-layer source groups:

- `final-gz-2345`
- `final-gz-678`
- `final-gz-901`
- `final-buildings-null`

The build pipeline normalizes those groups into one citywide age layer and pushes malformed dates into `unknown` instead of forcing bad year values into the map.

## Era bins

The current map uses these bands:

- `Before 1960`
- `1960-1969`
- `1970-1979`
- `1980-1989`
- `1990-1999`
- `2000-2009`
- `2010-2016`
- `Unknown`

## Repository layout

- `configs/age_bands.yml`: age-band config
- `docs/age-layer-method.md`: method for assembling the age layer
- `docs/project-brief.md`: project scope
- `scripts/inventory_source_data.py`: inventories the existing Seoul source parquet
- `scripts/build_seoul_age_layer.py`: builds the processed Seoul age-layer files
- `scripts/render_static_map.py`: exports the static map
- `data_processed/age_layers/`: local processed layer outputs
- `outputs/`: generated summaries and final map exports

## How to run

Create a Python environment with the dependencies in [pyproject.toml](pyproject.toml), then run:

```bash
python scripts/inventory_source_data.py
python scripts/build_seoul_age_layer.py
python scripts/render_static_map.py
```

## Generated outputs

The current build produces:

- `outputs/source_inventory.json`
- `outputs/age_layer_summary.json`
- `outputs/when-seoul-was-built-preview.svg`
- `outputs/when-seoul-was-built.pdf`

## Notes

- The processed age layers are kept locally in `data_processed/age_layers/`.
- The tracked preview image is a lightweight repo artifact for GitHub display.
- The styling can still be improved further with cleaner water, park, and road masking.
