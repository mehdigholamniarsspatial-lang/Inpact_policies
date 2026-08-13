"""
Raster catalogue + rendering for the Spatial Environmental Mapping panel.

Raster files live in ``data/Raster`` and follow the naming convention::

    <Year>_<Sector>_<Parameter>.tif

e.g. ``2019_B_Industry_pbenzoA.tif`` ->
    year      = 2019
    sector    = B_Industry        (every token between the first and the last)
    parameter = pbenzoA           (the final token)

This module:

* scans the folder and builds a nested catalogue
  ``{year: {sector: {parameter: filename}}}`` used to drive the three
  *cascading* dropdowns in the page (Year -> Sector -> Parameter). New files
  dropped into the folder are picked up automatically on the next request — no
  code change required.
* renders a selected raster to a web-ready RGBA PNG: the source grid is
  reprojected to Web-Mercator (EPSG:3857) so it lines up with the Leaflet
  basemap, a **rainbow** colour map is applied, and **zero / nodata cells are
  made fully transparent** (masked, never drawn).
* returns the lat/lng bounds + value range + colour-stops so the front end can
  position the overlay and draw a matching colour-bar legend.

Rendered results are cached in-memory keyed by (path, mtime, size) so repeated
selections are instant and the folder can still be edited live.
"""
from __future__ import annotations

import io
import importlib.util
import os
import re
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from PIL import Image

# rasterio (and its native GDAL libraries) is ONLY needed to render the raster
# .tif overlays in data/Raster/. It is a large, native-dependency-heavy package
# that frequently cannot be installed or loaded on serverless platforms such as
# Vercel (function size limits / missing GDAL shared libraries). Importing it at
# module load previously crashed the WHOLE app there — including the homepage —
# because views.py imports this module. We now import it lazily and optionally:
# the app, the catalogue scan and every other endpoint keep working, and only
# the raster-overlay endpoints degrade gracefully when rasterio is missing.
# Windows GIS installations (notably PostGIS) commonly set PROJ_LIB globally.
# A different PROJ version's proj.db is binary-incompatible with Rasterio's
# bundled GDAL/PROJ and makes every reprojection fail with "DATABASE.LAYOUT...".
# Point Rasterio at the data shipped with its own installation before importing
# it, while retaining compatibility with PROJ versions using either variable.
_rasterio_spec = importlib.util.find_spec("rasterio")
if _rasterio_spec and _rasterio_spec.submodule_search_locations:
    _rasterio_dir = Path(next(iter(_rasterio_spec.submodule_search_locations)))
    _bundled_proj_data = _rasterio_dir / "proj_data"
    if (_bundled_proj_data / "proj.db").is_file():
        os.environ["PROJ_DATA"] = str(_bundled_proj_data)
        os.environ["PROJ_LIB"] = str(_bundled_proj_data)

try:
    import rasterio
    from rasterio.transform import array_bounds
    from rasterio.warp import (
        Resampling,
        calculate_default_transform,
        reproject,
        transform_bounds,
    )
    RASTERIO_AVAILABLE = True
except Exception:  # pragma: no cover - depends on the deployment environment
    rasterio = None
    RASTERIO_AVAILABLE = False


class RasterRenderingUnavailable(RuntimeError):
    """Raised when a raster render is requested but rasterio cannot be loaded."""

# explorer/rasters.py -> explorer -> <project root>
BASE_DIR = Path(__file__).resolve().parent.parent
RASTER_DIR = BASE_DIR / "data" / "Raster"

# Pre-rendered overlays (PNG + JSON) produced by scripts/prerender_rasters.py.
# They are the fallback used on platforms where rasterio/GDAL cannot be
# installed (e.g. Vercel serverless): render() serves these files instead of
# reprojecting the .tif live, so the overlays behave identically everywhere.
PRERENDERED_DIR = BASE_DIR / "data" / "RasterPrerendered"

# Only real numeric years are accepted as the first token.
_YEAR_RE = re.compile(r"^\d{4}$")

# Cache of rendered overlays: key -> rendered dict. Guarded by a lock because
# Django's dev server / WSGI workers can render concurrently.
_RENDER_CACHE: Dict[tuple, dict] = {}
_RENDER_LOCK = threading.Lock()


# ---------------------------------------------------------------------------
# Rainbow colour map
# ---------------------------------------------------------------------------
def _rainbow_lut(n: int = 256) -> np.ndarray:
    """
    Return an ``(n, 3)`` uint8 lookup table for a blue -> red rainbow.

    Built from the HSV colour wheel with full saturation/value, sweeping the
    hue from 240 deg (blue, low values) down to 0 deg (red, high values). This
    is the classic "rainbow" ramp: blue -> cyan -> green -> yellow -> red.
    """
    t = np.linspace(0.0, 1.0, n)
    hue = (1.0 - t) * 240.0          # 240 (blue) -> 0 (red)
    hp = hue / 60.0                  # sector 0..4 (we never exceed 4)
    c = np.ones_like(t)              # chroma = S*V = 1
    x = c * (1.0 - np.abs((hp % 2.0) - 1.0))
    z = np.zeros_like(t)

    r = np.where(hp < 1, c, np.where(hp < 2, x, np.where(hp < 3, z, np.where(hp < 4, z, x))))
    g = np.where(hp < 1, x, np.where(hp < 2, c, np.where(hp < 3, c, np.where(hp < 4, x, z))))
    b = np.where(hp < 1, z, np.where(hp < 2, z, np.where(hp < 3, x, np.where(hp < 4, c, c))))

    rgb = np.stack([r, g, b], axis=1)
    return np.clip(rgb * 255.0, 0, 255).astype(np.uint8)


_RAINBOW = _rainbow_lut(256)


def _rainbow_stops(n: int = 9) -> List[str]:
    """A short list of ``#rrggbb`` stops (low -> high) for the legend gradient."""
    idx = np.linspace(0, 255, n).round().astype(int)
    return ["#%02x%02x%02x" % tuple(int(v) for v in _RAINBOW[i]) for i in idx]


# ---------------------------------------------------------------------------
# Filename parsing + catalogue
# ---------------------------------------------------------------------------
def parse_filename(name: str) -> Optional[Tuple[str, str, str]]:
    """
    Split ``2019_B_Industry_pbenzoA.tif`` -> ``("2019", "B_Industry", "pbenzoA")``.

    Returns ``None`` if the stem does not have at least Year/Sector/Parameter
    (i.e. three underscore-separated tokens) or the year token is not 4 digits.
    """
    stem = Path(name).stem
    parts = stem.split("_")
    if len(parts) < 3:
        return None
    year = parts[0]
    if not _YEAR_RE.match(year):
        return None
    parameter = parts[-1]
    sector = "_".join(parts[1:-1])
    if not sector or not parameter:
        return None
    return year, sector, parameter


def scan_catalog() -> Dict[str, Dict[str, Dict[str, str]]]:
    """
    Scan ``data/Raster`` and return the nested catalogue::

        { year: { sector: { parameter: filename } } }

    Anything that does not match the naming convention is ignored. Called on
    every request so newly-added files appear without restarting the server.
    """
    catalog: Dict[str, Dict[str, Dict[str, str]]] = {}
    if not RASTER_DIR.is_dir():
        return catalog
    for path in sorted(RASTER_DIR.iterdir()):
        if path.suffix.lower() not in (".tif", ".tiff"):
            continue
        parsed = parse_filename(path.name)
        if parsed is None:
            continue
        year, sector, parameter = parsed
        catalog.setdefault(year, {}).setdefault(sector, {})[parameter] = path.name
    return catalog


def resolve_path(year: str, sector: str, parameter: str) -> Optional[Path]:
    """
    Look up a (year, sector, parameter) selection in a freshly-scanned
    catalogue and return the file path, or ``None`` if it is not a valid
    combination. Resolving through the scan (rather than building a path from
    user input) prevents path traversal.
    """
    catalog = scan_catalog()
    name = catalog.get(year, {}).get(sector, {}).get(parameter)
    if not name:
        return None
    path = RASTER_DIR / name
    return path if path.is_file() else None


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------
def _render(path: Path) -> dict:
    """
    Reproject ``path`` to Web-Mercator, apply the rainbow colour map with zero /
    nodata masked transparent, and return a dict with:

        png      : PNG bytes (RGBA)
        bounds   : [[south, west], [north, east]]  (WGS84, for L.imageOverlay)
        vmin/vmax: value range used for the colour scale (0 if all-masked)
        all_zero : True when there is no non-zero data to display
        stops    : rainbow gradient stops (low -> high) for the legend
    """
    dst_crs = "EPSG:3857"
    with rasterio.open(path) as src:
        transform, width, height = calculate_default_transform(
            src.crs, dst_crs, src.width, src.height, *src.bounds
        )
        data = np.full((height, width), np.nan, dtype="float32")
        reproject(
            source=rasterio.band(src, 1),
            destination=data,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=transform,
            dst_crs=dst_crs,
            src_nodata=src.nodata,
            dst_nodata=np.nan,
            resampling=Resampling.nearest,  # keep the zero-mask crisp (no blending)
        )

    # Web-Mercator extent of the reprojected grid, then -> WGS84 for Leaflet.
    west, south, east, north = array_bounds(height, width, transform)
    w, s, e, n = transform_bounds(dst_crs, "EPSG:4326", west, south, east, north)
    bounds = [[s, w], [n, e]]

    # Valid = finite AND non-zero. Everything else is masked (transparent).
    valid = np.isfinite(data) & (data != 0.0)
    rgba = np.zeros((height, width, 4), dtype=np.uint8)

    if not valid.any():
        # Nothing to draw (e.g. an all-zero raster): fully transparent overlay.
        img = Image.fromarray(rgba, "RGBA")
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return {
            "png": buf.getvalue(),
            "bounds": bounds,
            "vmin": 0.0,
            "vmax": 0.0,
            "data_min": 0.0,
            "data_max": 0.0,
            "scale": "log",
            "all_zero": True,
            "stops": _rainbow_stops(),
        }

    vmin = float(np.nanmin(data[valid]))
    vmax = float(np.nanmax(data[valid]))

    # Emission rasters are strictly positive after masking and span several
    # orders of magnitude, so a *logarithmic* colour scale spreads the rainbow
    # across the data instead of washing everything to blue. Robust 2nd/98th
    # percentile endpoints stop a single hotspot (or a near-zero speck) from
    # dominating the ramp; values outside that window clamp to red / blue.
    vals = data[valid]
    lo = float(np.percentile(vals, 2))
    hi = float(np.percentile(vals, 98))
    if not (hi > lo > 0):           # fall back to full range if degenerate
        lo, hi = max(vmin, np.finfo("float32").tiny), vmax
    if hi <= lo:                    # single distinct value
        norm = np.full(data.shape, 0.5, dtype="float32")
    else:
        clipped = np.clip(data, lo, hi)
        norm = (np.log10(clipped) - np.log10(lo)) / (np.log10(hi) - np.log10(lo))
    # Replace masked/NaN cells with 0 before the integer cast (avoids warnings).
    norm = np.where(valid, norm, 0.0)
    idx = np.clip(norm * 255.0, 0, 255).astype(np.int32)

    rgba[..., :3] = _RAINBOW[idx]
    rgba[..., 3] = np.where(valid, 255, 0).astype(np.uint8)

    img = Image.fromarray(rgba, "RGBA")
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return {
        "png": buf.getvalue(),
        "bounds": bounds,
        # vmin/vmax describe the colour-scale endpoints (what the legend shows).
        "vmin": lo,
        "vmax": hi,
        "data_min": vmin,
        "data_max": vmax,
        "scale": "log",
        "all_zero": False,
        "stops": _rainbow_stops(),
    }


def _load_prerendered(path: Path) -> Optional[dict]:
    """
    Return the pre-rendered overlay (PNG bytes + metadata) for ``path`` if it
    exists in ``data/RasterPrerendered``, else ``None``.

    These files are produced offline by ``scripts/prerender_rasters.py`` and
    committed to the repository, which is how raster overlays keep working on
    serverless hosts (Vercel) where rasterio/GDAL cannot be installed.
    """
    import json

    stem = path.stem
    png_path = PRERENDERED_DIR / f"{stem}.png"
    meta_path = PRERENDERED_DIR / f"{stem}.json"
    if not (png_path.is_file() and meta_path.is_file()):
        return None
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        result = dict(meta)
        result["png"] = png_path.read_bytes()
        return result
    except (OSError, ValueError):
        return None


def render(path: Path) -> dict:
    """
    Cached wrapper that returns the rendered overlay for ``path``.

    Order of preference:
      1. live render with rasterio (local machines / full environments) —
         always reflects the current .tif on disk;
      2. pre-rendered PNG + JSON from ``data/RasterPrerendered`` (serverless
         deployments without GDAL);
      3. :class:`RasterRenderingUnavailable` if neither is possible.
    """
    if not RASTERIO_AVAILABLE:
        prerendered = _load_prerendered(path)
        if prerendered is not None:
            return prerendered
        raise RasterRenderingUnavailable(
            "rasterio is not installed/available in this environment and no "
            "pre-rendered overlay was found for this raster. Run "
            "scripts/prerender_rasters.py locally and commit "
            "data/RasterPrerendered/."
        )
    stat = path.stat()
    key = (str(path), int(stat.st_mtime), int(stat.st_size))
    with _RENDER_LOCK:
        cached = _RENDER_CACHE.get(key)
    if cached is not None:
        return cached
    result = _render(path)
    with _RENDER_LOCK:
        _RENDER_CACHE[key] = result
    return result
