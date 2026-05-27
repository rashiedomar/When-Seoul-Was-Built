# Project Brief

## Objective

Produce a static analytical map that answers a simple question:

`When was Seoul built?`

The intended output is a dense citywide figure that can stand on its own in a portfolio, report, or presentation.

## Target output

- one high-resolution Seoul map
- era-binned building or parcel geometries
- a readable legend
- minimal but strong title and subtitle treatment
- exportable `PNG` and later `PDF`

## Analytical posture

This is a data-analysis project with a cartographic finish.

The value comes from:

- source inventory
- cleaning and joining data
- defensible temporal bins
- consistent styling
- reproducible export steps

## Immediate constraints

- the local footprint parquet already exists and covers Seoul
- the local parquet does not yet expose a construction year field directly
- the earlier Seoul prototype already used public age-bucket layers that can guide the temporal model

## First deliverables

1. source inventory
2. era-bin definition
3. join strategy for adding construction age
4. first static draft map
