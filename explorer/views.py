"""
Views for the Ireland GHG Policy Impact Explorer.

The page is a single, self-contained HTML file (it inlines its own CSS and JS).
We read it from disk and return it verbatim, which deliberately bypasses
Django's template engine so the page's CSS/JS braces are never misinterpreted.

The one thing we inject is the emissions dataset: it is read from the editable
CSV at ``data/ghg_inventory.csv`` and spliced into two placeholders in the page
(``/*@INVENTORY@*/{}`` and ``/*@YEARS@*/[]``). Edit that CSV and reload the page
— the chart, indicator switcher and KPIs all recompute.
"""
import csv
import json
import logging
from pathlib import Path

from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from . import feedback_store
from . import edgar, inverse, rasters
from . import timeseries
from . import map_export as map_export_mod

logger = logging.getLogger(__name__)

# explorer/views.py -> explorer -> <project root>
BASE_DIR = Path(__file__).resolve().parent.parent
_PAGE_PATH = Path(__file__).resolve().parent / "page" / "index.html"
_PALETTES_PATH = Path(__file__).resolve().parent / "palettes.json"
_CSV_PATH = BASE_DIR / "data" / "ghg_inventory.csv"
_POLICIES_PATH = BASE_DIR / "data" / "policies.csv"

# Sectoral inventory (Main Sector -> Subsector time series), one wide CSV per gas.
# Each file: first column = sector/subsector name, remaining columns = years.
_SECTOR_DIR = BASE_DIR / "data" / "sector_inventory"
_SECTOR_FILES = {
    "Total GHG": "Total.csv",
    "CO₂": "CO2.csv",
    "CH₄": "CH4.csv",
    "N₂O": "N2O.csv",
}
# Normalise known typos / stray whitespace in the source spreadsheets so the
# row names match the hierarchy used by the page's Sector Explorer.
_SECTOR_NAME_FIXES = {
    "nann-energy products from fuels and solvent use":
        "Non-energy products from fuels and solvent use",
}


def _load_inventory(csv_path: Path):
    """
    Read the wide-format inventory CSV into the structure the page expects.

    Returns ``(real_data, years)`` where:
      * ``real_data`` maps each gas column header -> list of values (floats,
        or ``None`` for blank cells), aligned to ``years``.
      * ``years`` is the sorted list of integer years (the first CSV column).

    The gas column headers must match the keys used by the page's INDICATORS
    map (e.g. "All greenhouse gases", "CO2", "CH4 - (CO2 equivalent)", ...).
    """
    with csv_path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        # First column is the year; everything after is a gas series.
        gas_cols = [h.strip() for h in header[1:]]
        rows = []
        for raw in reader:
            if not raw or all(cell.strip() == "" for cell in raw):
                continue  # skip blank lines
            if raw[0].strip().startswith("#"):
                continue  # allow comment rows
            year = int(float(raw[0].strip()))
            values = []
            for cell in raw[1:]:
                cell = cell.strip()
                values.append(None if cell == "" else float(cell))
            # pad short rows so every gas stays aligned
            while len(values) < len(gas_cols):
                values.append(None)
            rows.append((year, values))

    rows.sort(key=lambda r: r[0])  # ascending years; arrays stay aligned
    years = [year for year, _ in rows]
    real_data = {
        gas: [vals[i] for _, vals in rows]
        for i, gas in enumerate(gas_cols)
    }
    return real_data, years


def _load_sector_inventory():
    """
    Read the per-gas sectoral CSVs into the structure the Sector Explorer expects.

    Returns ``(sector_data, years)`` where:
      * ``sector_data`` maps gas label -> { sector/subsector name -> [values] },
        values in kt CO2-eq (``None`` for blank/dash cells), aligned to ``years``.
      * ``years`` is the list of integer years taken from the CSV headers
        (all four files must share the same year columns).

    Raises ``FileNotFoundError`` if any of the four CSVs is missing, so the
    caller can fall back to an empty dataset.
    """
    def _cell(raw):
        cell = raw.strip().replace(",", "")
        if cell in ("", "-", "–", "NA", "NaN"):
            return None
        return float(cell)

    sector_data, years = {}, None
    for gas, fname in _SECTOR_FILES.items():
        path = _SECTOR_DIR / fname
        with path.open(newline="", encoding="utf-8-sig") as fh:
            reader = csv.reader(fh)
            header = next(reader)
            file_years = [int(float(h.strip())) for h in header[1:]]
            if years is None:
                years = file_years
            elif file_years != years:
                raise ValueError(f"{fname}: year columns differ from the other sector CSVs")

            table = {}
            for raw in reader:
                if not raw or all(c.strip() == "" for c in raw):
                    continue
                name = raw[0].strip()
                if not name or name.startswith("#"):
                    continue
                name = _SECTOR_NAME_FIXES.get(name, name)
                values = [_cell(c) for c in raw[1:]]
                while len(values) < len(years):
                    values.append(None)
                table[name] = values
            sector_data[gas] = table
    return sector_data, years


def _load_policies(csv_path: Path):
    """
    Read the climate-policy timeline CSV into a list of dicts.

    Expected columns: year, name, level, agency, sector, type, instrument,
    description, direction, outcome. ``level`` is one of International / EU /
    National / Target and drives the colour and the sidebar checkboxes.
    """
    policies = []
    with csv_path.open(newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            year_raw = (row.get("year") or "").strip()
            if not year_raw or year_raw.startswith("#"):
                continue
            policy = {k: (v or "").strip() for k, v in row.items()}
            policy["year"] = int(float(year_raw))
            policies.append(policy)
    policies.sort(key=lambda p: p["year"])
    return policies


def _render_page():
    """Read the page and splice in the inventory data from the CSV."""
    html = _PAGE_PATH.read_text(encoding="utf-8")
    try:
        real_data, years = _load_inventory(_CSV_PATH)
        inventory_json = json.dumps(real_data, ensure_ascii=False)
        years_json = json.dumps(years)
    except FileNotFoundError:
        # No dataset present: serve the page with an empty (but valid) dataset.
        inventory_json, years_json = "{}", "[]"

    try:
        policies_json = json.dumps(_load_policies(_POLICIES_PATH), ensure_ascii=False)
    except FileNotFoundError:
        policies_json = "[]"

    try:
        sector_data, sector_years = _load_sector_inventory()
        sectors_json = json.dumps(sector_data, ensure_ascii=False)
        sector_years_json = json.dumps(sector_years)
    except (FileNotFoundError, ValueError):
        # Missing/inconsistent sector CSVs: page falls back to inventory mode only.
        sectors_json, sector_years_json = "{}", "[]"

    html = html.replace("/*@INVENTORY@*/{}", inventory_json, 1)
    html = html.replace("/*@YEARS@*/[]", years_json, 1)
    html = html.replace("/*@POLICIES@*/[]", policies_json, 1)
    html = html.replace("/*@SECTORS@*/{}", sectors_json, 1)
    html = html.replace("/*@SECTOR_YEARS@*/[]", sector_years_json, 1)
    # Map colour palettes (explorer/palettes.json, the same list the JPEG export uses)
    try:
        palettes_json = _PALETTES_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        palettes_json = "{}"
    html = html.replace("/*@PALETTES@*/{}", palettes_json, 1)
    return html


def index(request):
    """Serve the Explorer single-page application with live CSV data."""
    return HttpResponse(_render_page())


def map_page(request):
    """
    Serve the Spatial Environmental Mapping panel on its own (the dashboard's
    "Open in new window" button). Same page, flagged with ``map-standalone`` on
    ``<html>`` so its CSS shows only the map workspace with a way back.
    """
    html = _render_page()
    # ?embed=1: shown in the dashboard's Spatial Mapping tab, under its own header and menu
    cls = "map-standalone map-embed" if request.GET.get("embed") == "1" else "map-standalone"
    html = html.replace('<html lang="en">', f'<html lang="en" class="{cls}">', 1)
    html = html.replace(
        "<title>Ireland Greenhouse Gas Policy Impact Explorer</title>",
        "<title>Spatial Environmental Mapping · Ireland GHG Policy Impact Explorer</title>", 1)
    return HttpResponse(html)


# ---------------------------------------------------------------------------
# Raster overlay endpoints
# ---------------------------------------------------------------------------
def raster_catalog(request):
    """
    Return the nested raster catalogue that drives the cascading dropdowns::

        { "2019": { "B_Industry": { "pbenzoA": "2019_B_Industry_pbenzoA.tif" } } }

    plus the display labels (names, groups, units, empty layers) from
    :func:`rasters.catalog_labels`.

    The folder is re-scanned on every call, so files added to ``data/Raster``
    appear automatically with no code change or server restart.
    """
    catalog = rasters.scan_catalog()
    return JsonResponse({"catalog": catalog, **rasters.catalog_labels(catalog)})


def _resolve_selection(request):
    """Shared helper: pull year/sector/parameter from the query string."""
    year = (request.GET.get("year") or "").strip()
    sector = (request.GET.get("sector") or "").strip()
    parameter = (request.GET.get("parameter") or "").strip()
    if not (year and sector and parameter):
        return None, JsonResponse(
            {"ok": False, "detail": "year, sector and parameter are required."},
            status=400,
        )
    path = rasters.resolve_path(year, sector, parameter)
    if path is None:
        return None, JsonResponse(
            {"ok": False, "detail": "Unknown raster selection."}, status=404
        )
    return path, None


def raster_meta(request):
    """
    Return overlay metadata (WGS84 bounds, value range, colour stops, all-zero
    flag) for a selected raster — everything the page needs to place the image
    and draw the matching colour-bar legend.
    """
    path, error = _resolve_selection(request)
    if error is not None:
        return error
    try:
        r = rasters.render(path)
    except rasters.RasterRenderingUnavailable:
        return JsonResponse(
            {"ok": False, "detail": "Raster overlays are unavailable in this deployment."},
            status=503,
        )
    except Exception:
        logger.exception("Failed to render raster metadata for %s", path)
        return JsonResponse(
            {"ok": False, "detail": "The selected raster could not be rendered."},
            status=500,
        )
    return JsonResponse(
        {
            "ok": True,
            "bounds": r["bounds"],
            "vmin": r["vmin"],
            "vmax": r["vmax"],
            "data_min": r.get("data_min", r["vmin"]),
            "data_max": r.get("data_max", r["vmax"]),
            "scale": r.get("scale", "linear"),
            "all_zero": r["all_zero"],
            "stops": r["stops"],
        }
    )


def raster_image(request):
    """
    Return the selected raster rendered as an RGBA PNG (rainbow colour map,
    zero/nodata transparent) for use as a Leaflet image overlay.
    """
    path, error = _resolve_selection(request)
    if error is not None:
        return error
    try:
        r = rasters.render(path)
    except rasters.RasterRenderingUnavailable:
        return JsonResponse(
            {"ok": False, "detail": "Raster overlays are unavailable in this deployment."},
            status=503,
        )
    except Exception:
        logger.exception("Failed to render raster image for %s", path)
        return JsonResponse(
            {"ok": False, "detail": "The selected raster could not be rendered."},
            status=500,
        )
    resp = HttpResponse(r["png"], content_type="image/png")
    resp["Cache-Control"] = "public, max-age=3600"
    return resp


def edgar_catalog(request):
    """Grid geometry, years, gases, sectors and credits for the EDGAR layers."""
    data = edgar.catalog()
    if not data:
        return JsonResponse({"ok": False, "detail": "EDGAR layers are not available."}, status=503)
    return JsonResponse({"ok": True, **data}, json_dumps_params={"ensure_ascii": False})


def edgar_layer(request):
    """Cell values, unit and colour scale for one EDGAR gas/sector/year/month."""
    q = {k: (request.GET.get(k) or "").strip() for k in ("gas", "sector", "year", "month")}
    try:
        data = edgar.layer(**q)
    except Exception:
        logger.exception("Failed to load EDGAR layer %s", q)
        return JsonResponse({"ok": False, "detail": "The EDGAR layer could not be loaded."}, status=500)
    if data is None:
        return JsonResponse({"ok": False, "detail": "Unknown EDGAR selection."}, status=404)
    resp = JsonResponse({"ok": True, **data}, json_dumps_params={"ensure_ascii": False})
    resp["Cache-Control"] = "public, max-age=3600"
    return resp


_TS_KEYS = ("dataset", "where", "agg", "gas", "sector", "step", "model", "transport", "estimate", "poly",
            "lat", "lng", "s", "w", "n", "e")


def map_timeseries(request):
    """Time series of one EDGAR / inverse-model layer at a pixel, a region or the whole of Ireland."""
    q = {k: (request.GET.get(k) or "").strip() for k in _TS_KEYS}
    try:
        data = timeseries.series(q)
    except timeseries.SelectionError as err:
        return JsonResponse({"ok": False, "detail": str(err)}, status=422)
    except Exception:
        logger.exception("Failed to build time series %s", q)
        return JsonResponse({"ok": False, "detail": "The time series could not be built."}, status=500)
    if data is None:
        return JsonResponse({"ok": False, "detail": "Unknown time series selection."}, status=404)
    resp = JsonResponse({"ok": True, **data}, json_dumps_params={"ensure_ascii": False})
    resp["Cache-Control"] = "public, max-age=3600"
    return resp


def inverse_catalog(request):
    """Grid geometry, runs and their years, gases and credits for the inverse-model layers."""
    data = inverse.catalog()
    if not data:
        return JsonResponse({"ok": False, "detail": "Inverse model layers are not available."}, status=503)
    return JsonResponse({"ok": True, **data}, json_dumps_params={"ensure_ascii": False})


def inverse_layer(request):
    """Prior / posterior cell values, uncertainty range and Ireland totals for one run and year."""
    q = {k: (request.GET.get(k) or "").strip() for k in ("model", "transport", "gas", "year")}
    try:
        data = inverse.layer(**q)
    except Exception:
        logger.exception("Failed to load inverse-model layer %s", q)
        return JsonResponse({"ok": False, "detail": "The inverse model layer could not be loaded."}, status=500)
    if data is None:
        return JsonResponse({"ok": False, "detail": "Unknown inverse model selection."}, status=404)
    resp = JsonResponse({"ok": True, **data}, json_dumps_params={"ensure_ascii": False})
    resp["Cache-Control"] = "public, max-age=3600"
    return resp


_LAYER_KEYS = ("year", "sector", "parameter", "gas", "month", "model", "transport", "estimate")
# Plus a second layer (b_*) and the difference mode when comparing two layers
_EXPORT_KEYS = ("dataset", "compare", "mode", *_LAYER_KEYS, *(f"b_{k}" for k in _LAYER_KEYS),
                "palette", "div_palette", "reverse")   # the colours chosen in the map's "Map style" step


def map_export(request, fmt):
    """
    Download the layer selected on the map as a GeoTIFF (``fmt="geotiff"``) or
    a JPEG map with legend (``fmt="jpeg"``). Same query as the layer endpoints
    plus ``dataset`` (mapeire | edgar | inverse).
    """
    if fmt not in ("geotiff", "jpeg"):
        return JsonResponse({"ok": False, "detail": "Format must be geotiff or jpeg."}, status=404)
    q = {k: (request.GET.get(k) or "").strip() for k in _EXPORT_KEYS}
    try:
        with map_export_mod.use_palette(map_export_mod.Palette.from_query(q)):
            layer = map_export_mod.build_layer(q)
            body, filename = (map_export_mod.geotiff if fmt == "geotiff" else map_export_mod.jpeg)(layer)
    except map_export_mod.SelectionError as exc:
        return JsonResponse({"ok": False, "detail": str(exc)}, status=404)
    except rasters.RasterRenderingUnavailable:
        return JsonResponse({"ok": False, "detail": "This MapEIre layer is unavailable in this deployment."}, status=503)
    except Exception:
        logger.exception("Failed to export map layer %s as %s", q, fmt)
        return JsonResponse({"ok": False, "detail": "The map could not be exported."}, status=500)
    resp = HttpResponse(body, content_type="image/tiff" if fmt == "geotiff" else "image/jpeg")
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    resp["Cache-Control"] = "public, max-age=3600"
    return resp


# ---------------------------------------------------------------------------
# Feedback endpoints
# ---------------------------------------------------------------------------
@csrf_exempt
@require_POST
def submit_feedback(request):
    """
    Accept a feedback submission (JSON or form-encoded) and persist it to the
    Excel workbook — committing to GitHub when configured, otherwise to local
    disk. Returns a small JSON status the front-end uses to confirm.
    """
    try:
        if request.content_type and "application/json" in request.content_type:
            data = json.loads(request.body.decode("utf-8") or "{}")
        else:
            data = request.POST.dict()
    except (ValueError, UnicodeDecodeError):
        return JsonResponse(
            {"ok": False, "detail": "Could not parse the submission."}, status=400
        )

    result = feedback_store.save_feedback(data)
    return JsonResponse(result, status=200 if result.get("ok") else 500)


def download_feedback(request):
    """
    Stream the current feedback workbook as an .xlsx download.

    Source of truth is GitHub when a token is configured, otherwise the local
    file. Useful as an admin convenience; the canonical copy also lives in the
    GitHub repo and can be downloaded directly from there.
    """
    content = feedback_store.get_workbook_bytes()
    if content is None:
        return HttpResponse(
            "No feedback has been recorded yet.",
            status=404,
            content_type="text/plain",
        )
    resp = HttpResponse(
        content,
        content_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
    )
    resp["Content-Disposition"] = 'attachment; filename="inpact_feedback.xlsx"'
    return resp
