"""
Pack the EDGAR Ireland GeoTIFFs in geotiff/ into compact grids the map can serve.

Why this exists
---------------
geotiff/ holds 1,200 GeoTIFFs (3 gases x 8 sectors x 25 years, monthly and
annual; see geotiff/README_EDGAR_Ireland_metadata.md). Reading them needs
rasterio, which Vercel cannot install. This script reads them once on a local
machine and writes, per gas and sector:

    data/EDGAR/<GAS>_<SECTOR>.npz   annual (years, cells) and monthly
                                    (years, 12, cells) float32 values for the
                                    949 cells inside the Republic of Ireland

plus data/EDGAR/edgar_metadata.json: the grid geometry, the cell index of
every valid cell, years, gas/sector labels, units, colour-scale limits and the
dataset credit. explorer/edgar.py serves these with numpy only.

Usage (from the project root, in an environment with rasterio installed):

    python scripts/build_edgar_grids.py
"""
import json
from pathlib import Path

import numpy as np
import rasterio

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "geotiff"
OUT_DIR = PROJECT_ROOT / "data" / "EDGAR"
RELEASE = "EDGAR_2025_GHG"

GASES = {
    "CO2": {"formula": "CO₂", "name": "Carbon dioxide (fossil)",
            "note": "Fossil CO₂ only; excludes biogenic CO₂ (CO₂bio)."},
    "CH4": {"formula": "CH₄", "name": "Methane", "note": ""},
    "N2O": {"formula": "N₂O", "name": "Nitrous oxide", "note": ""},
}

# From the "Sectors" and "Seasonal variation" tables of the README.
SECTORS = {
    "AGRICULTURE": ("Agriculture", "3A+3C+5A",
                    "Enteric fermentation, manure management, agricultural soils, "
                    "agricultural waste burning. CO₂ is from liming and urea, not fuel use."),
    "BUILDINGS": ("Buildings", "1A4+1A5",
                  "Fuel combustion in residential, commercial/institutional and "
                  "agriculture/forestry/fishing buildings."),
    "FUEL_EXPLOITATION": ("Fuel exploitation", "1A1b+1A1c+1A5biii+1B+5B",
                          "Fugitive emissions from coal, oil and gas; refineries and "
                          "transformation industry."),
    "IND_COMBUSTION": ("Industrial combustion", "1A2",
                       "Fuel combustion in manufacturing industries and construction."),
    "IND_PROCESSES": ("Industrial processes", "2",
                      "Process (non-combustion) emissions: chemicals, iron and steel, "
                      "cement and lime, solvents and product use."),
    "POWER_INDUSTRY": ("Power industry", "1A1a",
                       "Public electricity and heat production, allocated to power-plant "
                       "locations, so only a few cells are non-zero."),
    "TRANSPORT": ("Transport", "1A3",
                  "Road transport, rail, pipelines, off-road, and domestic aviation and "
                  "shipping that fall in land cells."),
    "WASTE": ("Waste", "4",
              "Solid waste landfills, waste incineration and wastewater handling."),
}

# Sectors whose monthly bands are annual / 12 (README, "Seasonal variation").
FLAT_MONTHLY = {
    ("CH4", "AGRICULTURE"), ("CH4", "FUEL_EXPLOITATION"), ("CH4", "WASTE"),
    ("CO2", "WASTE"), ("N2O", "AGRICULTURE"), ("N2O", "IND_PROCESSES"),
    ("N2O", "WASTE"),
}


def _path(gas, sector, year, annual):
    sub = "annual" if annual else "monthly"
    suffix = "_annual" if annual else ""
    return SRC_DIR / gas / sector / sub / f"IE_{RELEASE}_{gas}_{year}_bkl_{sector}_emi{suffix}.tif"


def _scale(values):
    """Fixed log colour-scale limits over all years: P1 of non-zero cells .. max."""
    pos = values[np.isfinite(values) & (values > 0)]
    if pos.size == 0:
        return None
    hi = float(pos.max())
    lo = max(float(np.percentile(pos, 1)), hi * 1e-5)
    return {"lo": lo, "hi": hi}


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    years = sorted({int(p.name.split("_")[5]) for p in SRC_DIR.glob("CO2/AGRICULTURE/annual/*.tif")})

    with rasterio.open(_path("CO2", "AGRICULTURE", years[0], True)) as src:
        t, rows, cols = src.transform, src.height, src.width
        mask = np.isfinite(src.read(1))
    cells = np.flatnonzero(mask.ravel())

    scales, totals = {}, {}
    for gas in GASES:
        for sector in SECTORS:
            annual = np.empty((len(years), cells.size), dtype="float32")
            monthly = np.empty((len(years), 12, cells.size), dtype="float32")
            for i, year in enumerate(years):
                with rasterio.open(_path(gas, sector, year, True)) as src:
                    annual[i] = src.read(1).ravel()[cells]
                with rasterio.open(_path(gas, sector, year, False)) as src:
                    monthly[i] = src.read().reshape(12, -1)[:, cells]
            # 0 = no emission assigned; NaN would only come from a mask mismatch.
            annual, monthly = np.nan_to_num(annual), np.nan_to_num(monthly)
            np.savez_compressed(OUT_DIR / f"{gas}_{sector}.npz", annual=annual, monthly=monthly)
            key = f"{gas}|{sector}"
            scales[key] = {"annual": _scale(annual), "monthly": _scale(monthly)}
            totals[key] = [round(float(v), 3) for v in annual.sum(axis=1)]
            print(f"{key}: 2024 total {totals[key][-1]:,.0f} t")

    meta = {
        "_about": "Written by scripts/build_edgar_grids.py from geotiff/ "
                  "(see geotiff/README_EDGAR_Ireland_metadata.md). Do not edit by hand.",
        "release": RELEASE,
        "grid": {"west": t.c, "north": t.f, "res": t.a, "rows": rows, "cols": cols,
                 "crs": "EPSG:4326 (WGS 84)", "cells": cells.tolist()},
        "years": years,
        "gases": GASES,
        "sectors": {k: {"name": n, "ipcc": c, "contents": d, "order": i}
                    for i, (k, (n, c, d)) in enumerate(SECTORS.items())},
        "flat_monthly": sorted(f"{g}|{s}" for g, s in FLAT_MONTHLY),
        "scales": scales,
        "national_totals": totals,
        "units": {
            "annual": "t {gas} per 0.1° cell per year",
            "monthly": "t {gas} per 0.1° cell, {month}",
        },
        "source": {
            "dataset": "EDGAR Community GHG Database (EDGAR_2025_GHG)",
            "credit": "European Commission JRC / IEA",
            "url": "https://edgar.jrc.ec.europa.eu/dataset_ghg2025",
            "resolution": "0.1° × 0.1° (≈ 11 × 7 km)",
            "coverage": "Republic of Ireland (cells whose centre lies inside the boundary)",
            "boundary": "Natural Earth",
            "notes": [
                "Values are mass of each gas, not CO₂-equivalent.",
                "Spatial pattern is modelled from proxies; do not read single cells as facility data.",
                "Monthly values are annual totals split with sector profiles, not monthly observations.",
                "Recent years are EDGAR fast-track estimates.",
            ],
        },
    }
    (OUT_DIR / "edgar_metadata.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Wrote {len(scales)} grids and edgar_metadata.json to {OUT_DIR}")


if __name__ == "__main__":
    main()
