"""
EDGAR gridded emissions (CO2, CH4, N2O) for the Spatial Environmental Mapping panel.

The source GeoTIFFs in ``geotiff/`` are packed by ``scripts/build_edgar_grids.py``
into ``data/EDGAR/<GAS>_<SECTOR>.npz`` plus ``data/EDGAR/edgar_metadata.json``,
so this module needs numpy only and works on Vercel without rasterio.

The page draws each 0.1° cell itself (so it can show the value on hover), so
the API returns the raw cell values in the order of ``grid.cells`` rather than
a rendered image.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Dict, Optional

import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
EDGAR_DIR = BASE_DIR / "data" / "EDGAR"
METADATA_PATH = EDGAR_DIR / "edgar_metadata.json"

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

_META_CACHE: Dict[str, object] = {"mtime": None, "data": {}}
_GRID_CACHE: Dict[str, dict] = {}
_LOCK = threading.Lock()


def load_metadata() -> dict:
    """Return ``edgar_metadata.json``, re-read whenever the file changes."""
    try:
        mtime = METADATA_PATH.stat().st_mtime
    except OSError:
        return {}
    if _META_CACHE["mtime"] != mtime:
        try:
            data = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
        except ValueError:
            data = {}
        _META_CACHE.update(mtime=mtime, data=data)
    return _META_CACHE["data"]  # type: ignore[return-value]


def _load_grid(gas: str, sector: str) -> dict:
    """Load (and cache) the annual / monthly arrays for one gas and sector."""
    key = f"{gas}_{sector}"
    with _LOCK:
        cached = _GRID_CACHE.get(key)
    if cached is None:
        with np.load(EDGAR_DIR / f"{key}.npz") as npz:
            cached = {"annual": npz["annual"], "monthly": npz["monthly"]}
        with _LOCK:
            _GRID_CACHE[key] = cached
    return cached


def layer(gas: str, sector: str, year: str, month: str) -> Optional[dict]:
    """
    Cell values and labels for one selection, or ``None`` if it is not valid.

    ``month`` is ``"annual"`` or ``"1"``..``"12"``; month *n* is band *n* of
    the monthly GeoTIFF. Inputs are checked against the metadata, never used
    to build a path directly.
    """
    meta = load_metadata()
    if gas not in meta.get("gases", {}) or sector not in meta.get("sectors", {}):
        return None
    try:
        year_idx = meta["years"].index(int(year))
    except (ValueError, KeyError):
        return None
    annual = month == "annual"
    if not annual and month not in {str(m) for m in range(1, 13)}:
        return None

    grid = _load_grid(gas, sector)
    values = grid["annual"][year_idx] if annual else grid["monthly"][year_idx, int(month) - 1]
    period = "annual" if annual else "monthly"
    formula = meta["gases"][gas]["formula"]
    month_label = "" if annual else f"{MONTHS[int(month) - 1]} {year}"
    nonzero = values[values > 0]
    key = f"{gas}|{sector}"
    return {
        "values": [float(f"{v:.5g}") for v in values.tolist()],
        "period": period,
        "month_label": month_label,
        "unit": meta["units"][period].format(gas=formula, month=month_label),
        "scale": meta["scales"][key][period],
        "total": float(values.sum(dtype="float64")),
        "max": float(values.max()) if values.size else 0.0,
        "nonzero_cells": int(nonzero.size),
        "all_zero": nonzero.size == 0,
        "flat_monthly": key in meta.get("flat_monthly", []),
    }


def catalog() -> dict:
    """Everything the page needs to build the EDGAR dropdowns and legend."""
    meta = load_metadata()
    if not meta:
        return {}
    return {k: meta[k] for k in
            ("release", "grid", "years", "gases", "sectors", "national_totals", "source")
            if k in meta} | {"months": MONTHS}
