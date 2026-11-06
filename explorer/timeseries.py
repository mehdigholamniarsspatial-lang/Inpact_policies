"""
Time series of EDGAR / PARIS inverse-model cells for the map window's Time series panel.

One request returns a whole series (every year, or every month for EDGAR) for
one layer definition and one spatial selection:

* ``where=pixel``  – the grid cell under ``lat`` / ``lng``
* ``where=region`` – cells whose centre lies inside ``s``, ``w``, ``n``, ``e``,
  a drawn ``poly`` or a ``county`` (data/boundaries/counties.json)
* ``where=whole``  – every Ireland cell of the dataset

For a region or the whole grid the cells are combined per time step with
``agg=mean``, ``agg=median`` or ``agg=sum`` (the total of the cells: EDGAR cells
are already totals per cell; inverse-model fluxes are multiplied by the cell
area and Ireland's share of the cell, giving t yr⁻¹). Inputs are checked against the metadata, never
used to build a path directly.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Optional

import numpy as np

from . import edgar, inverse

AGGREGATES = {"mean": np.nanmean, "median": np.nanmedian, "sum": np.nansum}
WHERE = ("pixel", "region", "whole")


class SelectionError(ValueError):
    """The request is well formed but selects nothing (e.g. a pixel outside Ireland)."""


def _num(q: dict, key: str) -> float:
    try:
        v = float(q.get(key, ""))
    except ValueError:
        raise SelectionError(f"Missing or invalid {key}.")
    if not np.isfinite(v):
        raise SelectionError(f"Missing or invalid {key}.")
    return v


def _bbox(q: dict):
    s, w, n, e = (_num(q, k) for k in ("s", "w", "n", "e"))
    return min(s, n), min(w, e), max(s, n), max(w, e)


MAX_VERTICES = 300


def _polygon(text: str) -> np.ndarray:
    """``poly=lat,lng;lat,lng;...`` → (k, 2) array of vertices."""
    try:
        pts = np.array([[float(v) for v in p.split(",")] for p in text.split(";") if p.strip()], dtype="float64")
    except ValueError:
        raise SelectionError("Invalid polygon.")
    if pts.ndim != 2 or pts.shape[1] != 2 or not 3 <= len(pts) <= MAX_VERTICES or not np.isfinite(pts).all():
        raise SelectionError(f"A polygon needs 3 to {MAX_VERTICES} vertices.")
    return pts


def _in_polygon(lat: np.ndarray, lng: np.ndarray, pts: np.ndarray) -> np.ndarray:
    """Even-odd ray casting of the cell centres against the polygon."""
    inside = np.zeros(lat.shape, dtype=bool)
    j = len(pts) - 1
    for i in range(len(pts)):
        (yi, xi), (yj, xj) = pts[i], pts[j]
        if yi != yj:
            crosses = (yi > lat) != (yj > lat)
            inside ^= crosses & (lng < (xj - xi) * (lat - yi) / (yj - yi) + xi)
        j = i
    return inside


COUNTIES_PATH = Path(__file__).resolve().parent.parent / "data" / "boundaries" / "counties.json"


@lru_cache(maxsize=1)
def counties() -> dict:
    """County name → list of (k, 2) lat/lng rings, from scripts/build_counties.py."""
    try:
        data = json.loads(COUNTIES_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    return {c["name"]: [np.asarray(r, dtype="float64") for r in c["rings"]] for c in data.get("counties", [])}


def _in_rings(lat: np.ndarray, lng: np.ndarray, rings) -> np.ndarray:
    """Even-odd over every ring: islands add cells, holes take them out."""
    inside = np.zeros(lat.shape, dtype=bool)
    for r in rings:
        inside ^= _in_polygon(lat, lng, r)
    return inside


def _pick(q: dict, centres_lat: np.ndarray, centres_lng: np.ndarray, pixel_index):
    """Positions (into the value arrays) of the selected cells, and whether the region fell back to one cell."""
    where = q.get("where")
    if where == "whole":
        return np.arange(centres_lat.size), False
    if where == "region":
        if q.get("county"):
            rings = counties().get(q["county"])
            if rings is None:
                raise SelectionError("Unknown county.")
            sel = np.flatnonzero(_in_rings(centres_lat, centres_lng, rings))
            big = max(rings, key=len)
            centre = big.mean(axis=0)
        elif q.get("poly"):
            pts = _polygon(q["poly"])
            sel = np.flatnonzero(_in_polygon(centres_lat, centres_lng, pts))
            centre = pts.mean(axis=0)
        else:
            s, w, n, e = _bbox(q)
            sel = np.flatnonzero((centres_lat >= s) & (centres_lat <= n) & (centres_lng >= w) & (centres_lng <= e))
            centre = ((s + n) / 2, (w + e) / 2)
        if sel.size:
            return sel, False
        # Smaller than one cell of this dataset (e.g. the 25 km inverse grid): use the cell at its centre
        pos = pixel_index(float(centre[0]), float(centre[1]))
        if pos is None:
            raise SelectionError("No grid cell of this dataset lies inside the region; draw it over Ireland.")
        return np.array([pos]), True
    pos = pixel_index(_num(q, "lat"), _num(q, "lng"))
    if pos is None:
        raise SelectionError("This point is outside the dataset's Ireland cells; click on Ireland.")
    return np.array([pos]), False


def _agg(q: dict) -> str:
    """How the cells are combined; a single pixel is its own value."""
    return "mean" if q.get("where") == "pixel" else (q.get("agg") or "mean")


def _combine(block: np.ndarray, agg: str) -> list:
    """``block`` is time × cells; returns one value per time step (None where nothing is finite)."""
    out = []
    for row in block:
        finite = row[np.isfinite(row)]
        out.append(float(f"{AGGREGATES[agg](finite):.6g}") if finite.size else None)
    return out


def _edgar(q: dict) -> Optional[dict]:
    meta = edgar.load_metadata()
    gas, sector, step = q.get("gas"), q.get("sector"), q.get("step") or "annual"
    if gas not in meta.get("gases", {}) or sector not in meta.get("sectors", {}) or step not in ("annual", "monthly"):
        return None
    g = meta["grid"]
    cells = np.asarray(g["cells"])
    rows, cols = cells // g["cols"], cells % g["cols"]
    lat = g["north"] - (rows + 0.5) * g["res"]
    lng = g["west"] + (cols + 0.5) * g["res"]
    lookup = {int(c): i for i, c in enumerate(cells)}

    def pixel_index(la, ln):
        r, c = int(np.floor((g["north"] - la) / g["res"])), int(np.floor((ln - g["west"]) / g["res"]))
        if not (0 <= r < g["rows"] and 0 <= c < g["cols"]):
            return None
        return lookup.get(r * g["cols"] + c)

    sel, fallback = _pick(q, lat, lng, pixel_index)
    grid = edgar._load_grid(gas, sector)
    years = meta["years"]
    formula = meta["gases"][gas]["formula"]
    if step == "annual":
        block = grid["annual"][:, sel]
        t = [float(y) for y in years]
        labels = [str(y) for y in years]
        unit = f"t {formula} per 0.1° cell per year"
    else:
        block = grid["monthly"][:, :, sel].reshape(len(years) * 12, sel.size)
        t = [round(y + m / 12, 4) for y in years for m in range(12)]   # Jan at the year tick, like annual points
        labels = [f"{edgar.MONTHS[m]} {y}" for y in years for m in range(12)]
        unit = f"t {formula} per 0.1° cell per month"
    agg = _agg(q)
    if agg == "sum":
        unit = f"t {formula} per {'month' if step == 'monthly' else 'year'} (total of the cells)"
    return {
        "t": t, "labels": labels, "values": _combine(block.astype("float64"), agg),
        "unit": unit, "formula": formula, "n_cells": int(sel.size), "fallback": fallback,
        "cell": _edgar_cell(g, int(cells[sel[0]])) if q.get("where") == "pixel" else None,
        "title": f"EDGAR {formula} · {meta['sectors'][sector]['name']}" + (" · monthly" if step == "monthly" else ""),
    }


def _edgar_cell(g: dict, idx: int) -> list:
    n = g["north"] - (idx // g["cols"]) * g["res"]
    w = g["west"] + (idx % g["cols"]) * g["res"]
    return [[round(n - g["res"], 4), round(w, 4)], [round(n, 4), round(w + g["res"], 4)]]


def _inverse(q: dict) -> Optional[dict]:
    meta = inverse.load_metadata()
    model, transport, gas = q.get("model"), q.get("transport"), q.get("gas")
    estimate = q.get("estimate") or "posterior"
    run = meta.get("runs", {}).get(f"{model}|{transport}|{gas}")
    if run is None or estimate not in ("prior", "posterior", "difference"):
        return None
    g = meta["grid"]
    frac = np.asarray(meta["country_fraction"][model], dtype="float64")
    ireland = np.flatnonzero(frac > 0)                     # the modellers' Ireland attribution area
    rows, cols = ireland // g["cols"], ireland % g["cols"]
    lat = g["north"] - (rows + 0.5) * g["dlat"]
    lng = g["west"] + (cols + 0.5) * g["dlon"]
    lookup = {int(c): i for i, c in enumerate(ireland)}

    def pixel_index(la, ln):
        r, c = int(np.floor((g["north"] - la) / g["dlat"])), int(np.floor((ln - g["west"]) / g["dlon"]))
        if not (0 <= r < g["rows"] and 0 <= c < g["cols"]):
            return None
        return lookup.get(r * g["cols"] + c)

    sel, fallback = _pick(q, lat, lng, pixel_index)
    cells = ireland[sel]
    grid = inverse._load_grid(model, transport, gas)
    n_years = len(run["years"])
    if estimate == "difference":
        block = grid["posterior"][:n_years, cells] - grid["prior"][:n_years, cells]
    else:
        block = grid[estimate][:n_years, cells]
    agg = _agg(q)
    formula = meta["gases"][gas]["formula"]
    unit = meta["unit"].format(gas=formula)
    block = block.astype("float64")
    if agg == "sum":   # kg km⁻² yr⁻¹ × km² × Ireland share of the cell → t yr⁻¹
        weight = np.asarray(meta["cell_area_km2"], dtype="float64")[cells] * frac[cells] / 1000.0
        block = block * weight
        unit = f"t {formula} yr⁻¹ (total of the cells)"
    out = {
        "t": [float(y) for y in run["years"]], "labels": [str(y) for y in run["years"]],
        "values": _combine(block, agg),
        "unit": unit, "formula": formula, "n_cells": int(sel.size), "fallback": fallback,
        "cell": None,
        "title": f"Inverse {formula} · {model} {transport} · {estimate.capitalize()}",
    }
    if q.get("where") == "pixel":
        idx = int(cells[0])
        n = g["north"] - (idx // g["cols"]) * g["dlat"]
        w = g["west"] + (idx % g["cols"]) * g["dlon"]
        out["cell"] = [[round(n - g["dlat"], 4), round(w, 4)], [round(n, 4), round(w + g["dlon"], 4)]]
        if estimate != "difference":                        # 1σ-equivalent range of the single cell
            out["lo"] = _combine(grid[f"{estimate}_lo"][:n_years, cells].astype("float64"), "mean")
            out["hi"] = _combine(grid[f"{estimate}_hi"][:n_years, cells].astype("float64"), "mean")
    return out


def series(q: dict) -> Optional[dict]:
    """The series for one request, ``None`` for an unknown layer; raises ``SelectionError``."""
    if q.get("where") not in WHERE:
        return None
    if (q.get("agg") or "mean") not in AGGREGATES:
        return None
    dataset = q.get("dataset")
    if dataset == "edgar":
        return _edgar(q)
    if dataset == "inverse":
        return _inverse(q)
    return None
