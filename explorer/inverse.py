"""
PARIS inverse-model (top-down) CH4 and N2O fluxes for the Spatial Environmental Mapping panel.

The GeoTIFFs in ``InversionModel/InversionModelGeotiff/`` are packed by
``scripts/build_inverse_grids.py`` into ``data/InverseModel/<MODEL>_<TRANSPORT>_<GAS>.npz``
plus ``data/InverseModel/inverse_metadata.json``, so this module needs numpy
only and works on Vercel without rasterio.

One request returns prior, posterior and their 15.9th–84.1st percentile range
for a year, so the page can switch between Prior, Posterior and Difference
(posterior − prior) without another round trip.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Dict, Optional

import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
INVERSE_DIR = BASE_DIR / "data" / "InverseModel"
METADATA_PATH = INVERSE_DIR / "inverse_metadata.json"

_LAYERS = ("prior", "posterior", "prior_lo", "prior_hi", "posterior_lo", "posterior_hi")

_META_CACHE: Dict[str, object] = {"mtime": None, "data": {}}
_GRID_CACHE: Dict[str, dict] = {}
_LOCK = threading.Lock()


def load_metadata() -> dict:
    """Return ``inverse_metadata.json``, re-read whenever the file changes."""
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


def _load_grid(model: str, transport: str, gas: str) -> dict:
    """Load (and cache) the prior / posterior arrays for one run."""
    key = f"{model}_{transport}_{gas}"
    with _LOCK:
        cached = _GRID_CACHE.get(key)
    if cached is None:
        with np.load(INVERSE_DIR / f"{key}.npz") as npz:
            cached = {name: npz[name] for name in _LAYERS}
        with _LOCK:
            _GRID_CACHE[key] = cached
    return cached


def _round(values: np.ndarray) -> list:
    return [None if not np.isfinite(v) else float(f"{v:.5g}") for v in values.tolist()]


def layer(model: str, transport: str, gas: str, year: str) -> Optional[dict]:
    """
    Cell values and Ireland totals for one run and year, or ``None`` if the
    selection is not valid. Inputs are checked against the metadata, never
    used to build a path directly.
    """
    meta = load_metadata()
    run = meta.get("runs", {}).get(f"{model}|{transport}|{gas}")
    if run is None:
        return None
    try:
        idx = run["years"].index(int(year))
    except ValueError:
        return None

    grid = _load_grid(model, transport, gas)
    return {
        **{name: _round(grid[name][idx]) for name in _LAYERS},
        "country_fraction": meta["country_fraction"][model],
        "unit": meta["unit"].format(gas=meta["gases"][gas]["formula"]),
        "scale": meta["scales"][gas],
        "total_prior": run["total_prior"][idx],
        "total_posterior": run["total_posterior"][idx],
        "urr": run["urr"][idx],
    }


def catalog() -> dict:
    """Everything the page needs to build the Inverse Model dropdowns and legend."""
    meta = load_metadata()
    if not meta:
        return {}
    runs = {key: {"years": run["years"]} for key, run in meta["runs"].items()}
    return {k: meta[k] for k in
            ("grid", "cell_area_km2", "models", "transports", "gases", "source")
            if k in meta} | {"runs": runs}
