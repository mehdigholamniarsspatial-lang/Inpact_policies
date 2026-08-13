"""
trend_views.py
==============
JSON API for the Trend Analysis tab (piecewise regression dashboard).

This replaces the standalone Streamlit deployment: the same numerical
engine (see ``trend_engine.py``) now runs inside this Django program and
reads the SAME sector-inventory CSVs (``data/sector_inventory/``) that the
Explorer tab already uses, so there is a single source of truth for data.

Endpoints
---------
GET  /api/trend/catalog/   -> gases, their sector lists, and the year axis
GET  /api/trend/series/    -> raw (year, value) series for one gas + sector
POST /api/trend/fit/       -> piecewise fit + stats + diagnostics as JSON
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import numpy as np
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from . import trend_engine

# explorer/trend_views.py -> explorer -> <project root>
BASE_DIR = Path(__file__).resolve().parent.parent
_SECTOR_DIR = BASE_DIR / "data" / "sector_inventory"

# Gas label -> CSV file. Same files that feed the Explorer's Sector Explorer.
_GAS_FILES = {
    "Total GHG": "Total.csv",
    "CO₂": "CO2.csv",
    "CH₄": "CH4.csv",
    "N₂O": "N2O.csv",
}

_NAME_FIXES = {
    "nann-energy products from fuels and solvent use":
        "Non-energy products from fuels and solvent use",
}


class TrendDataError(Exception):
    """Raised when the sector-inventory CSVs cannot be read as expected."""


# ----------------------------------------------------------------------
# Data loading (wide CSV: first column = sector, remaining columns = years)
# ----------------------------------------------------------------------
def _cell(raw: str):
    cell = (raw or "").strip().replace(",", "")
    if cell in ("", "-", "–", "NA", "NaN"):
        return None
    return float(cell)


def _load_gas_table(gas: str):
    """Return ``(years, {sector: [values]})`` for one gas label."""
    fname = _GAS_FILES.get(gas)
    if fname is None:
        raise TrendDataError(f"Unknown gas '{gas}'.")
    path = _SECTOR_DIR / fname
    if not path.exists():
        raise TrendDataError(f"Data file missing: {path.name}")

    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        years = [int(float(h.strip())) for h in header[1:]]
        table = {}
        for raw in reader:
            if not raw or all(c.strip() == "" for c in raw):
                continue
            name = raw[0].strip()
            if not name or name.startswith("#"):
                continue
            name = _NAME_FIXES.get(name, name)
            values = [_cell(c) for c in raw[1:]]
            while len(values) < len(years):
                values.append(None)
            table[name] = values
    return years, table


def _get_series(gas: str, sector: str):
    """Return cleaned ``(t, y, report)`` numpy arrays for one gas + sector."""
    years, table = _load_gas_table(gas)
    if sector not in table:
        raise TrendDataError(f"Unknown sector '{sector}' for gas '{gas}'.")
    raw = table[sector]
    t_all = np.asarray(years, dtype=float)
    y_all = np.asarray([np.nan if v is None else v for v in raw], dtype=float)
    mask = np.isfinite(y_all)
    report = {
        "n_raw": int(len(y_all)),
        "n_used": int(mask.sum()),
        "n_dropped": int(len(y_all) - mask.sum()),
    }
    return t_all[mask], y_all[mask], report


def _finite(x):
    """JSON-safe float (NaN/inf -> None)."""
    x = float(x)
    return x if math.isfinite(x) else None


# ----------------------------------------------------------------------
# Endpoints
# ----------------------------------------------------------------------
@require_GET
def trend_catalog(request):
    """Gas -> ordered sector list, plus the shared year axis."""
    catalog, years_out = {}, None
    try:
        for gas in _GAS_FILES:
            years, table = _load_gas_table(gas)
            catalog[gas] = list(table.keys())
            years_out = years_out or years
    except TrendDataError as exc:
        return JsonResponse({"ok": False, "detail": str(exc)}, status=500)
    return JsonResponse({"ok": True, "gases": catalog, "years": years_out})


@require_GET
def trend_series(request):
    """Raw series for one gas + sector (used to pre-plot before fitting)."""
    gas = (request.GET.get("gas") or "").strip()
    sector = (request.GET.get("sector") or "").strip()
    if not (gas and sector):
        return JsonResponse(
            {"ok": False, "detail": "gas and sector are required."}, status=400
        )
    try:
        t, y, report = _get_series(gas, sector)
    except TrendDataError as exc:
        return JsonResponse({"ok": False, "detail": str(exc)}, status=404)
    return JsonResponse(
        {
            "ok": True,
            "years": [int(v) for v in t],
            "values": [float(v) for v in y],
            "cleaning": report,
        }
    )


@csrf_exempt
@require_POST
def trend_fit(request):
    """
    Fit the piecewise regression and return everything the front-end plots:

    Request JSON:
        { "gas": "...", "sector": "...", "breakpoints": [2005, 2015],
          "method": "ols" | "huber" | "theilsen", "confidence": 0.95,
          "mann_kendall_segments": false }

    Response JSON:
        segments (stats-table rows + per-segment fitted line and CI band),
        mann_kendall, sens_slope, optional segment_mann_kendall,
        residual diagnostics, cleaning report.
    """
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except (ValueError, UnicodeDecodeError):
        return JsonResponse(
            {"ok": False, "detail": "Could not parse the request body."}, status=400
        )

    gas = (payload.get("gas") or "").strip()
    sector = (payload.get("sector") or "").strip()
    method = (payload.get("method") or "ols").strip().lower()
    enable_segment_mk = payload.get("mann_kendall_segments", False) is True
    if method not in ("ols", "huber", "theilsen"):
        return JsonResponse(
            {"ok": False, "detail": f"Unknown method '{method}'."}, status=400
        )
    try:
        confidence = float(payload.get("confidence") or trend_engine.CONFIDENCE_LEVEL)
        if not (0.5 < confidence < 1.0):
            raise ValueError
    except (TypeError, ValueError):
        return JsonResponse(
            {"ok": False, "detail": "confidence must be a number in (0.5, 1)."},
            status=400,
        )

    # ---- data --------------------------------------------------------
    try:
        t, y, report = _get_series(gas, sector)
    except TrendDataError as exc:
        return JsonResponse({"ok": False, "detail": str(exc)}, status=404)
    if len(t) < trend_engine.MIN_POINTS_PER_SEGMENT:
        return JsonResponse(
            {"ok": False, "detail": "Too few valid data points in this series."},
            status=422,
        )

    # ---- breakpoints (validated against the observed time range) -----
    raw_bps = payload.get("breakpoints") or []
    try:
        bps = sorted(float(b) for b in raw_bps)
    except (TypeError, ValueError):
        return JsonResponse(
            {"ok": False, "detail": "breakpoints must be a list of numbers."},
            status=400,
        )
    t_min, t_max = float(t.min()), float(t.max())
    inside = [b for b in bps if t_min < b < t_max]
    dropped_bps = [b for b in bps if b not in inside]
    # collapse duplicates
    inside = sorted(set(inside))

    # ---- fit ---------------------------------------------------------
    try:
        segments = trend_engine.fit_piecewise_regression(
            t, y, inside, method=method, confidence=confidence
        )
    except ValueError as exc:
        return JsonResponse({"ok": False, "detail": str(exc)}, status=422)

    seg_payload = []
    for seg in segments:
        lo_band, hi_band = trend_engine.prediction_band(seg, confidence)
        seg_payload.append(
            {
                **seg.as_table_row(),
                "t": [float(v) for v in seg.t_values],
                "y_pred": [_finite(v) for v in seg.y_predicted],
                "band_low": [_finite(v) for v in lo_band],
                "band_high": [_finite(v) for v in hi_band],
            }
        )

    # ---- diagnostics -------------------------------------------------
    fitted = np.concatenate([s.y_predicted for s in segments])
    resid = np.concatenate([s.residuals for s in segments])
    t_used = np.concatenate([s.t_values for s in segments])
    counts, edges = np.histogram(resid, bins=min(15, max(5, len(resid) // 3)))

    mk = trend_engine.mann_kendall_test(y)
    sen = trend_engine.sens_slope(t, y, confidence)
    segment_mk = []
    if enable_segment_mk:
        for seg in segments:
            seg_test = trend_engine.mann_kendall_test(seg.y_values)
            seg_sen = trend_engine.sens_slope(
                seg.t_values, seg.y_values, confidence
            )
            is_significant = seg_test["p_value"] < 0.05
            segment_mk.append(
                {
                    "segment": seg.segment_index,
                    "start": seg.start,
                    "end": seg.end,
                    "period": f"{seg.start:g}\u2013{seg.end:g}",
                    "n": seg.n,
                    "S": seg_test["S"],
                    "Z": _finite(seg_test["Z"]),
                    "p_value": _finite(seg_test["p_value"]),
                    "trend": seg_test["trend"],
                    "significant": bool(is_significant),
                    "significance": (
                        "Significant (p < 0.05)"
                        if is_significant
                        else "Not significant (p \u2265 0.05)"
                    ),
                    "sens_slope": _finite(seg_sen["slope"]),
                }
            )

    return JsonResponse(
        {
            "ok": True,
            "gas": gas,
            "sector": sector,
            "method": method,
            "confidence": confidence,
            "cleaning": report,
            "years": [float(v) for v in t],
            "values": [float(v) for v in y],
            "breakpoints_used": inside,
            "breakpoints_dropped": dropped_bps,
            "segments": seg_payload,
            "segment_mann_kendall_enabled": enable_segment_mk,
            "segment_mann_kendall": segment_mk,
            "mann_kendall": {k: (_finite(v) if isinstance(v, float) else v)
                             for k, v in mk.items()},
            "sens_slope": {k: _finite(v) for k, v in sen.items()},
            "diagnostics": {
                "t": [float(v) for v in t_used],
                "fitted": [_finite(v) for v in fitted],
                "residuals": [_finite(v) for v in resid],
                "hist_counts": [int(c) for c in counts],
                "hist_edges": [float(e) for e in edges],
            },
        }
    )
