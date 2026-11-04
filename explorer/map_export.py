"""
Downloads of the layer shown in the Spatial Environmental Mapping panel.

For the current selection of any of the three datasets this builds

* a **GeoTIFF**: the cell values (EDGAR, inverse model) as one float32 band in
  WGS 84, written by a small TIFF writer below so no GDAL is needed on Vercel.
  MapEIre ships only pre-rendered colour overlays in the deployment, so its
  GeoTIFF is the original ``data/Raster`` file when that is on disk, otherwise
  the rendered colours (RGBA, Web Mercator) of the overlay the map shows;
* a **JPEG** map: the layer in the same colours as the web map, Ireland's
  coastline (``data/boundaries/ireland_outline.json``, Natural Earth), lat/lon
  ticks, a title, a colour-bar legend, key figures and the data source.

Selections are validated by the dataset modules (``edgar.layer``,
``inverse.layer``, ``rasters.resolve_path``); user input never builds a path.
"""
from __future__ import annotations

import colorsys
import io
import json
import math
import struct
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import List, Optional, Sequence, Tuple
from xml.sax.saxutils import escape

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from . import edgar, inverse, rasters

BASE_DIR = Path(__file__).resolve().parent.parent
OUTLINE_PATH = BASE_DIR / "data" / "boundaries" / "ireland_outline.json"
FONT_DIR = BASE_DIR / "data" / "fonts"
NODATA = -9999.0
R_EARTH = 6378137.0
VIEW = (-11.0, 51.25, -5.3, 55.55)   # west, south, east, north of the JPEG map frame

RGB = Tuple[int, int, int]


# ---------------------------------------------------------------------------
# Colours (the same ramps as the web map)
# ---------------------------------------------------------------------------
def rainbow(t: float) -> RGB:
    """Blue -> red rainbow, HSV hue 240 -> 0 (``GRID_UI.rainbow`` on the page)."""
    t = min(max(t, 0.0), 1.0)
    r, g, b = colorsys.hls_to_rgb((1 - t) * 240 / 360, 0.5, 1.0)
    return round(r * 255), round(g * 255), round(b * 255)


_DIV_NEG, _DIV_MID, _DIV_POS = (33, 102, 172), (247, 247, 247), (178, 24, 43)


def diverging(t: float) -> RGB:
    """Blue (negative) -> white -> red (positive), t in [-1, 1]."""
    a, b = (_DIV_MID, _DIV_NEG) if t < 0 else (_DIV_MID, _DIV_POS)
    k = min(abs(t), 1.0)
    return tuple(round(a[i] + (b[i] - a[i]) * k) for i in range(3))  # type: ignore[return-value]


def _hex(c: str) -> RGB:
    c = c.lstrip("#")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


def _fade(c: RGB, alpha: float) -> RGB:
    """Blend ``c`` over white (the faded cells of the web map)."""
    return tuple(round(255 + (v - 255) * alpha) for v in c)  # type: ignore[return-value]


_SUP = str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹")


def fmt(v: float) -> str:
    """Number formatting of the page's ``fmtVal`` (2.6 × 10⁻⁵, 1,234, 0.559)."""
    if v == 0:
        return "0"
    a = abs(v)
    if a < 1e-3 or a >= 1e7:
        m, e = f"{v:.1e}".split("e")
        return f"{m} × 10{str(int(e)).translate(_SUP)}"
    if a >= 1000:
        return f"{round(v):,}"
    return f"{float(f'{v:.3g}'):g}"


# ---------------------------------------------------------------------------
# What one download describes
# ---------------------------------------------------------------------------
@dataclass
class Legend:
    title: str
    unit: str
    kind: str                       # "log" | "diverging" | "stops"
    lo: float = 0.0
    hi: float = 1.0
    stops: Sequence[RGB] = ()       # kind == "stops": colour ramp bottom -> top
    ticks: Sequence[Tuple[float, str]] = ()   # (position 0..1, label)
    swatches: Sequence[Tuple[RGB, str]] = ()  # extra boxes under the bar
    note: str = ""


@dataclass
class Layer:
    stem: str                        # file name without extension
    title: str
    subtitle: str
    legend: Legend
    source: str
    facts: List[Tuple[str, str]] = field(default_factory=list)
    # Cells: (west, south, east, north, RGB) in degrees, drawn as rectangles
    cells: List[Tuple[float, float, float, float, RGB]] = field(default_factory=list)
    # Or a pre-rendered RGBA overlay in Web Mercator with its WGS 84 bounds
    overlay: Optional[Image.Image] = None
    overlay_bounds: Optional[Tuple[float, float, float, float]] = None  # w, s, e, n
    # GeoTIFF content
    tif_values: Optional[np.ndarray] = None            # float32 2-D, NODATA outside
    tif_geo: Optional[Tuple[float, float, float, float]] = None   # west, north, dx, dy (deg)
    tif_bytes: Optional[bytes] = None                   # an original file to pass through
    tif_meta: dict = field(default_factory=dict)


class SelectionError(ValueError):
    """The query does not describe a valid layer."""


def _slug(*parts: str) -> str:
    out = "_".join(p for p in parts if p)
    return "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in out)


def _log_ticks(lo: float, hi: float, n: int = 5) -> List[Tuple[float, str]]:
    ticks = []
    for i in range(n):
        t = i / (n - 1)
        v = 10 ** (math.log10(lo) + t * (math.log10(hi) - math.log10(lo)))
        label = fmt(v)
        if i == 0:
            label = "≤ " + label
        elif i == n - 1:
            label = "≥ " + label
        ticks.append((t, label))
    return ticks


# ---------------------------------------------------------------------------
# Dataset -> Layer
# ---------------------------------------------------------------------------
def _edgar_layer(q: dict) -> Layer:
    data = edgar.layer(q.get("gas", ""), q.get("sector", ""), q.get("year", ""), q.get("month", ""))
    if data is None:
        raise SelectionError("Unknown EDGAR selection.")
    meta = edgar.load_metadata()
    gas, sector = meta["gases"][q["gas"]], meta["sectors"][q["sector"]]
    grid = meta["grid"]
    west, north, res, rows, cols = grid["west"], grid["north"], grid["res"], grid["rows"], grid["cols"]
    lo, hi = data["scale"]["lo"], data["scale"]["hi"]
    annual = data["period"] == "annual"
    period = f"{q['year']} annual total" if annual else data["month_label"]

    arr = np.full(rows * cols, NODATA, dtype=np.float32)
    arr[np.asarray(grid["cells"])] = np.asarray(data["values"], dtype=np.float32)
    zero = (235, 238, 241)
    cells = []
    for idx, v in zip(grid["cells"], data["values"]):
        r, c = divmod(idx, cols)
        w, n = west + c * res, north - r * res
        if v > 0:
            t = (math.log10(min(max(v, lo), hi)) - math.log10(lo)) / (math.log10(hi) - math.log10(lo))
            colour = rainbow(t)
        else:
            colour = zero
        cells.append((w, n - res, w + res, n, colour))

    src = meta["source"]
    years = meta["years"]
    legend = Legend(
        title=f"{gas['formula']} · {period}", unit=data["unit"], kind="log", lo=lo, hi=hi,
        ticks=_log_ticks(lo, hi), swatches=[(zero, "0 (no emission assigned)")],
        note=f"Log scale, fixed over {years[0]}–{years[-1]} · mass of gas, not CO₂-eq",
    )
    return Layer(
        stem=_slug("EDGAR", q["gas"], q["sector"], q["year"], "annual" if annual else f"m{int(q['month']):02d}"),
        title=f"EDGAR · {gas['formula']} emissions from {sector['name'].lower()}",
        subtitle=f"{period}   [{data['unit']}]",
        legend=legend,
        source=f"{src['dataset']} · {src['credit']} · {src['url']}",
        facts=[
            ("Ireland total", f"{fmt(data['total'])} t {gas['formula']}"),
            ("Sector", f"{sector['name']} (IPCC {sector['ipcc']})"),
            ("Cells with emission", f"{data['nonzero_cells']} of {len(grid['cells'])}"),
            ("Resolution", src["resolution"]),
        ],
        cells=cells,
        tif_values=arr.reshape(rows, cols), tif_geo=(west, north, res, res),
        tif_meta={"DATASET": src["dataset"], "GAS": gas["formula"], "SECTOR": sector["name"],
                  "PERIOD": period, "UNITS": data["unit"], "SOURCE": src["url"]},
    )


_ESTIMATES = {"posterior": "Posterior", "prior": "Prior", "difference": "Difference (posterior − prior)"}


def _inverse_layer(q: dict) -> Layer:
    data = inverse.layer(q.get("model", ""), q.get("transport", ""), q.get("gas", ""), q.get("year", ""))
    est = q.get("estimate", "")
    if data is None or est not in _ESTIMATES:
        raise SelectionError("Unknown inverse model selection.")
    meta = inverse.load_metadata()
    gas = meta["gases"][q["gas"]]
    grid = meta["grid"]
    west, north, dlon, dlat = grid["west"], grid["north"], grid["dlon"], grid["dlat"]
    rows, cols = grid["rows"], grid["cols"]
    prior = np.array([np.nan if v is None else v for v in data["prior"]], dtype=np.float64)
    post = np.array([np.nan if v is None else v for v in data["posterior"]], dtype=np.float64)
    values = post - prior if est == "difference" else (post if est == "posterior" else prior)
    frac = data["country_fraction"]
    s = data["scale"]

    cells = []
    for i, v in enumerate(values):
        if not np.isfinite(v):
            continue
        if est == "difference":
            colour = diverging(v / s["difference"]["limit"])
        else:
            flo, fhi = s["flux"]["lo"], s["flux"]["hi"]
            colour = rainbow((math.log10(min(max(v, flo), fhi)) - math.log10(flo)) / (math.log10(fhi) - math.log10(flo)))
        if not frac[i] > 0:
            colour = _fade(colour, 0.45)
        r, c = divmod(i, cols)
        w, n = west + c * dlon, north - r * dlat
        cells.append((w, n - dlat, w + dlon, n, colour))

    arr = np.where(np.isfinite(values), values, NODATA).astype(np.float32).reshape(rows, cols)
    if est == "difference":
        lim = s["difference"]["limit"]
        legend = Legend(
            title=f"{gas['formula']} — {q['year']} — Difference", unit=data["unit"], kind="diverging",
            lo=-lim, hi=lim,
            ticks=[(0, f"≤ −{fmt(lim)}"), (0.25, f"−{fmt(lim / 2)}"), (0.5, "0"),
                   (0.75, f"+{fmt(lim / 2)}"), (1, f"≥ +{fmt(lim)}")],
            swatches=[(_fade(diverging(0.5), 0.45), "Outside the Ireland attribution area")],
            note="Linear, symmetric · fixed for all models and years",
        )
    else:
        legend = Legend(
            title=f"{gas['formula']} — {q['year']} — {_ESTIMATES[est]}", unit=data["unit"], kind="log",
            lo=s["flux"]["lo"], hi=s["flux"]["hi"], ticks=_log_ticks(s["flux"]["lo"], s["flux"]["hi"]),
            swatches=[(_fade(rainbow(0.6), 0.45), "Outside the Ireland attribution area")],
            note="Log scale · fixed for all models and years",
        )
    src = meta["source"]
    diff = data["total_posterior"] - data["total_prior"]
    what = "total flux difference" if est == "difference" else f"total flux — {_ESTIMATES[est]}"
    return Layer(
        stem=_slug("PARIS", q["model"], q["transport"], q["gas"], q["year"], est),
        title=f"{q['model']} {q['transport']} · Ireland · PARIS inverse model",
        subtitle=f"{gas['formula']} {what} — {q['year']}   [{data['unit']}]",
        legend=legend,
        source=f"{src['dataset']} · {src['credit']} · doi:{src['doi']}",
        facts=[
            ("Ireland posterior", f"{data['total_posterior']:,.2f} Gg {gas['formula']} yr⁻¹"),
            ("Ireland prior", f"{data['total_prior']:,.2f} Gg ({gas['prior']})"),
            ("Difference", f"{diff:+,.2f} Gg ({diff / data['total_prior'] * 100:+.1f}%)"),
            ("Constraint", f"{data['urr']:.2f} (σ posterior / σ prior)"),
            ("Resolution", src["resolution"]),
        ],
        cells=cells,
        tif_values=arr, tif_geo=(west, north, dlon, dlat),
        tif_meta={"DATASET": src["dataset"], "MODEL": q["model"], "TRANSPORT": q["transport"],
                  "GAS": gas["formula"], "YEAR": q["year"], "ESTIMATE": _ESTIMATES[est],
                  "UNITS": data["unit"], "SOURCE": src["url"]},
    )


def _mapeire_layer(q: dict) -> Layer:
    year, sector, param = q.get("year", ""), q.get("sector", ""), q.get("parameter", "")
    path = rasters.resolve_path(year, sector, param)
    if path is None:
        raise SelectionError("Unknown MapEIre selection.")
    r = rasters.render(path)
    p, s = rasters.describe_parameter(param), rasters.describe_sector(sector)
    src = rasters.load_metadata().get("source", {})
    (south, west), (north, east) = r["bounds"]
    img = Image.open(io.BytesIO(r["png"])).convert("RGBA")
    is_log = r.get("scale") == "log" and r["vmin"] > 0 and r["vmax"] > 0
    unit = p["unit_long"] or p["unit"] or "Unit not stated in the MapEIre report"
    vmin, vmax = r["vmin"], r["vmax"]
    mid = math.sqrt(vmin * vmax) if is_log else (vmin + vmax) / 2
    legend = Legend(
        title=f"{p['label']} — {year}", unit=unit, kind="stops", lo=vmin, hi=vmax,
        stops=[_hex(c) for c in r["stops"]],
        ticks=[(0, ("≤ " if r["data_min"] < vmin else "") + fmt(vmin)), (0.5, fmt(mid)),
               (1, ("≥ " if r["data_max"] > vmax else "") + fmt(vmax))],
        note=("Log scale" if is_log else "Linear scale") + " · cells with zero emission not shown",
    )
    facts = [("Sector", f"{s['code']} · {s['name']}" if s["code"] else s["name"]),
             ("Resolution", src.get("resolution", "")), ("Projection", src.get("projection", ""))]
    if r["data_max"] > vmax:
        facts.insert(1, ("Maximum cell", f"{fmt(r['data_max'])} {p['unit'] or ''}".strip()))

    layer = Layer(
        stem=_slug("MapEIre", year, sector, param.removeprefix("p")),
        title=f"MapEIre · {p['label']}",
        subtitle=f"{s['name']} — {year}" + (f"   [{p['unit_long'] or p['unit']}]" if p["unit"] else ""),
        legend=legend,
        source=f"{src.get('dataset', 'MapEIre')} · {src.get('credit', '')} · EPA Research Report 317",
        facts=facts,
        overlay=img, overlay_bounds=(west, south, east, north),
    )
    if path.is_file():
        layer.tif_bytes = path.read_bytes()        # the original values, when deployed
    else:
        layer.tif_meta = {"DATASET": src.get("dataset", "MapEIre"), "POLLUTANT": p["label"],
                          "SECTOR": s["name"], "YEAR": year,
                          "NOTE": "Rendered colours of the web map overlay, not emission values "
                                  "(the source rasters are not part of this deployment)."}
    return layer


def build_layer(q: dict) -> Layer:
    dataset = q.get("dataset", "")
    if dataset == "edgar":
        return _edgar_layer(q)
    if dataset == "inverse":
        return _inverse_layer(q)
    if dataset == "mapeire":
        return _mapeire_layer(q)
    raise SelectionError("Unknown dataset.")


# ---------------------------------------------------------------------------
# GeoTIFF (baseline TIFF + GeoKeys, uncompressed, one strip)
# ---------------------------------------------------------------------------
def _merc(lon: float, lat: float) -> Tuple[float, float]:
    return (R_EARTH * math.radians(lon),
            R_EARTH * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)))


def _tiff(pixels: np.ndarray, pixel_scale: Tuple[float, float], tiepoint: Tuple[float, float],
          epsg: int, metadata: dict, nodata: Optional[float]) -> bytes:
    """Write a GeoTIFF: float32 single band, or uint8 RGBA (shape rows × cols × 4)."""
    rgba = pixels.ndim == 3
    rows, cols = pixels.shape[:2]
    data = np.ascontiguousarray(pixels.astype("<f4" if not rgba else "u1")).tobytes()
    spp = 4 if rgba else 1

    if epsg == 4326:
        keys = [1, 1, 0, 4, 1024, 0, 1, 2, 1025, 0, 1, 1, 2048, 0, 1, 4326, 2054, 0, 1, 9102]
    else:
        keys = [1, 1, 0, 4, 1024, 0, 1, 1, 1025, 0, 1, 1, 3072, 0, 1, epsg, 3076, 0, 1, 9001]
    gdal_md = "<GDALMetadata>" + "".join(
        f'<Item name="{escape(k)}">{escape(str(v))}</Item>' for k, v in metadata.items()) + "</GDALMetadata>"

    # (tag, type, values); types: 2 ASCII, 3 SHORT, 4 LONG, 12 DOUBLE
    entries = [
        (256, 4, [cols]), (257, 4, [rows]),
        (258, 3, [8] * 4 if rgba else [32]), (259, 3, [1]), (262, 3, [2 if rgba else 1]),
        (273, 4, [0]),                     # StripOffsets, patched below
        (277, 3, [spp]), (278, 4, [rows]), (279, 4, [len(data)]), (284, 3, [1]),
    ]
    if rgba:
        entries.append((338, 3, [2]))      # ExtraSamples: unassociated alpha
    entries += [
        (339, 3, [1] * 4 if rgba else [3]),
        (33550, 12, [pixel_scale[0], pixel_scale[1], 0.0]),
        (33922, 12, [0.0, 0.0, 0.0, tiepoint[0], tiepoint[1], 0.0]),
        (34735, 3, keys),
        (42112, 2, gdal_md),
    ]
    if nodata is not None:
        entries.append((42113, 2, f"{nodata:g}"))
    entries.sort(key=lambda e: e[0])

    size = {2: 1, 3: 2, 4: 4, 12: 8}
    fmt_char = {3: "H", 4: "I", 12: "d"}
    ifd_offset = 8
    ifd_len = 2 + 12 * len(entries) + 4
    extra = bytearray()
    extra_base = ifd_offset + ifd_len
    packed = []
    for tag, typ, vals in entries:
        if typ == 2:
            raw = vals.encode("utf-8") + b"\0"
            count = len(raw)
        else:
            raw = struct.pack("<" + fmt_char[typ] * len(vals), *vals)
            count = len(vals)
        if len(raw) <= 4:
            packed.append([tag, typ, count, raw.ljust(4, b"\0"), None])
        else:
            if len(extra) % 2:
                extra += b"\0"
            packed.append([tag, typ, count, None, extra_base + len(extra)])
            extra += raw
    data_offset = extra_base + len(extra)
    if data_offset % 2:
        extra += b"\0"
        data_offset += 1

    out = bytearray(b"II*\0" + struct.pack("<I", ifd_offset))
    out += struct.pack("<H", len(packed))
    for tag, typ, count, inline, offset in packed:
        if tag == 273:
            inline = struct.pack("<I", data_offset)
        out += struct.pack("<HHI", tag, typ, count) + (inline if inline is not None else struct.pack("<I", offset))
    out += struct.pack("<I", 0)
    out += extra
    out += data
    return bytes(out)


def geotiff(layer: Layer) -> Tuple[bytes, str]:
    """GeoTIFF bytes and file name for ``layer``."""
    if layer.tif_bytes is not None:
        return layer.tif_bytes, f"{layer.stem}.tif"
    if layer.tif_values is not None:
        west, north, dx, dy = layer.tif_geo  # type: ignore[misc]
        return _tiff(layer.tif_values, (dx, dy), (west, north), 4326, layer.tif_meta, NODATA), f"{layer.stem}.tif"
    # MapEIre fallback: the overlay's RGBA pixels, already in Web Mercator
    w, s, e, n = layer.overlay_bounds  # type: ignore[misc]
    (x0, y0), (x1, y1) = _merc(w, s), _merc(e, n)
    img = layer.overlay
    px = np.asarray(img, dtype=np.uint8)
    scale = ((x1 - x0) / img.width, (y1 - y0) / img.height)
    return _tiff(px, scale, (x0, y1), 3857, layer.tif_meta, None), f"{layer.stem}_rendered-colours.tif"


# ---------------------------------------------------------------------------
# JPEG map
# ---------------------------------------------------------------------------
SS = 2                    # supersampling factor (drawn at 2x, then reduced)
W, H = 2000, 1500
NAVY, TEXT, MUTED, GRID = (22, 50, 79), (28, 43, 58), (92, 107, 122), (214, 221, 228)


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    return ImageFont.truetype(str(FONT_DIR / name), size * SS)


def _outline() -> List[List[Tuple[float, float]]]:
    try:
        data = json.loads(OUTLINE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [[tuple(p) for p in r["ring"]] for r in data.get("rings", [])]


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, width: int) -> List[str]:
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=font) <= width or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def jpeg(layer: Layer) -> Tuple[bytes, str]:
    """A print-ready JPEG of ``layer``: map, coastline, axes, legend, figures and source."""
    s = SS
    img = Image.new("RGB", (W * s, H * s), "white")
    d = ImageDraw.Draw(img)

    # Title and subtitle
    for text, size, bold, colour, y in ((layer.title, 46, True, NAVY, 52), (layer.subtitle, 30, True, (44, 62, 80), 122)):
        f = _font(size, bold)
        while d.textlength(text, font=f) > (W - 120) * s and size > 18:
            size -= 2
            f = _font(size, bold)
        d.text((W * s / 2, y * s), text, font=f, fill=colour, anchor="mt")

    # Map frame in Web Mercator, fitted into the left box
    west, south, east, north = VIEW
    (mx0, my0), (mx1, my1) = _merc(west, south), _merc(east, north)
    box_l, box_t, box_w, box_h = 250, 200, 1000, 1150
    k = min(box_w / (mx1 - mx0), box_h / (my1 - my0))
    fw, fh = (mx1 - mx0) * k, (my1 - my0) * k
    fl, ft = box_l + (box_w - fw) / 2, box_t + (box_h - fh) / 2

    def xy(lon: float, lat: float) -> Tuple[float, float]:
        x, y = _merc(lon, lat)
        return (fl + (x - mx0) * k) * s, (ft + (my1 - y) * k) * s

    frame = [fl * s, ft * s, (fl + fw) * s, (ft + fh) * s]
    layer_img = Image.new("RGBA", img.size, (255, 255, 255, 0))
    ld = ImageDraw.Draw(layer_img)
    if layer.overlay is not None:
        w, so, e, n = layer.overlay_bounds  # type: ignore[misc]
        (x0, y0), (x1, y1) = xy(w, n), xy(e, so)
        ov = layer.overlay.resize((max(1, round(x1 - x0)), max(1, round(y1 - y0))), Image.NEAREST)
        layer_img.alpha_composite(ov, (round(x0), round(y0)))
    for w, so, e, n, colour in layer.cells:
        (x0, y0), (x1, y1) = xy(w, n), xy(e, so)
        ld.rectangle([x0, y0, x1, y1], fill=colour + (255,))
    # Keep the layer inside the frame
    clip = Image.new("L", img.size, 0)
    ImageDraw.Draw(clip).rectangle(frame, fill=255)
    layer_img.putalpha(Image.composite(layer_img.getchannel("A"), clip, clip))
    img.paste(layer_img, (0, 0), layer_img)

    # Graticule, coastline, frame and ticks
    tick_f = _font(26, True)
    for lon in range(math.ceil(west), math.floor(east) + 1):
        x, _ = xy(lon, south)
        for yy in range(int(frame[1]), int(frame[3]), 18 * s):
            d.line([x, yy, x, min(yy + 8 * s, frame[3])], fill=GRID, width=s)
        d.line([x, frame[3], x, frame[3] + 10 * s], fill=TEXT, width=2 * s)
        d.text((x, frame[3] + 18 * s), f"{abs(lon)}°W", font=tick_f, fill=TEXT, anchor="mt")
    for lat in range(math.ceil(south), math.floor(north) + 1):
        _, y = xy(west, lat)
        for xx in range(int(frame[0]), int(frame[2]), 18 * s):
            d.line([xx, y, min(xx + 8 * s, frame[2]), y], fill=GRID, width=s)
        d.line([frame[0] - 10 * s, y, frame[0], y], fill=TEXT, width=2 * s)
        d.text((frame[0] - 18 * s, y), f"{lat}°N", font=tick_f, fill=TEXT, anchor="rm")
    for ring in _outline():
        pts = [xy(lon, lat) for lon, lat in ring]
        d.line(pts + [pts[0]], fill=(34, 40, 49), width=2 * s, joint="curve")
    d.rectangle(frame, outline=TEXT, width=2 * s)

    # Legend panel
    lg = layer.legend
    px0, py0, pw = 1330, 300, 600
    pad = 30
    title_f, unit_f, tick_f2, small_f = _font(30, True), _font(24), _font(22), _font(19)
    lines = _wrap(d, lg.title, title_f, (pw - 2 * pad) * s)
    unit_lines = _wrap(d, lg.unit, unit_f, (pw - 2 * pad) * s)
    bar_h, bar_w = 360, 46
    y = py0 + pad
    title_h = len(lines) * 40 + len(unit_lines) * 32 + 18
    note_lines = _wrap(d, lg.note, small_f, (pw - 2 * pad) * s) if lg.note else []
    panel_h = pad + title_h + bar_h + 20 + len(lg.swatches) * 40 + len(note_lines) * 26 + pad + 10
    d.rounded_rectangle([px0 * s, py0 * s, (px0 + pw) * s, (py0 + panel_h) * s], radius=10 * s,
                        fill=(248, 250, 252), outline=(85, 95, 108), width=2 * s)
    for ln in lines:
        d.text(((px0 + pad) * s, y * s), ln, font=title_f, fill=TEXT)
        y += 40
    for ln in unit_lines:
        d.text(((px0 + pad) * s, y * s), ln, font=unit_f, fill=MUTED)
        y += 32
    y += 18
    bx0, by0 = px0 + pad, y
    for i in range(bar_h * s):
        t = 1 - i / (bar_h * s - 1)                 # top = high
        if lg.kind == "diverging":
            c = diverging(2 * t - 1)
        elif lg.kind == "stops":
            pos = t * (len(lg.stops) - 1)
            a = int(min(pos, len(lg.stops) - 2))
            f_ = pos - a
            c = tuple(round(lg.stops[a][j] + (lg.stops[a + 1][j] - lg.stops[a][j]) * f_) for j in range(3))
        else:
            c = rainbow(t)
        d.line([bx0 * s, by0 * s + i, (bx0 + bar_w) * s, by0 * s + i], fill=c)
    d.rectangle([bx0 * s, by0 * s, (bx0 + bar_w) * s, (by0 + bar_h) * s], outline=(120, 128, 138), width=s)
    for t, label in lg.ticks:
        ty = by0 + (1 - t) * bar_h
        d.line([(bx0 + bar_w) * s, ty * s, (bx0 + bar_w + 10) * s, ty * s], fill=TEXT, width=s)
        d.text(((bx0 + bar_w + 18) * s, ty * s), label, font=tick_f2, fill=TEXT, anchor="lm")
    y = by0 + bar_h + 20
    for colour, label in lg.swatches:
        d.rectangle([bx0 * s, y * s, (bx0 + bar_w) * s, (y + 24) * s], fill=colour, outline=(120, 128, 138), width=s)
        d.text(((bx0 + bar_w + 18) * s, (y + 12) * s), label, font=small_f, fill=TEXT, anchor="lm")
        y += 40
    for ln in note_lines:
        d.text(((px0 + pad) * s, y * s), ln, font=small_f, fill=MUTED)
        y += 26

    # Key figures under the legend
    y = py0 + panel_h + 30
    key_f, val_f = _font(20, True), _font(20)
    key_w = max((d.textlength(k, font=key_f) / s for k, _ in layer.facts), default=0) + 22
    for key, val in layer.facts:
        if y > 1330:
            break
        d.text((px0 * s, y * s), key, font=key_f, fill=MUTED)
        for ln in _wrap(d, val, val_f, (pw - key_w) * s):
            d.text(((px0 + key_w) * s, y * s), ln, font=val_f, fill=TEXT)
            y += 28
        y += 6

    # Footer: source and provenance
    foot_f = _font(18)
    foot = [f"Source: {layer.source}",
            f"Coastline: Natural Earth · INPACT Ireland Greenhouse Gas Policy Impact Explorer · generated {date.today():%d %b %Y}"]
    yy = H - 92
    for text in foot:
        for ln in _wrap(d, text, foot_f, (W - 160) * s):
            d.text((80 * s, yy * s), ln, font=foot_f, fill=MUTED)
            yy += 25

    out = io.BytesIO()
    img.resize((W, H), Image.LANCZOS).save(out, format="JPEG", quality=92, dpi=(200, 200), optimize=True)
    return out.getvalue(), f"{layer.stem}.jpg"
