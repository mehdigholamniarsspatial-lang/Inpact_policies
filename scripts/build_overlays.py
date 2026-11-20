"""
Build the vector overlay layers of the Spatial Environmental Mapping panel
("Air Quality" button → Layer Overlay) from their source shapefiles.

Run once, offline, when a source shapefile changes:
    python scripts/build_overlays.py                         # every layer in LAYERS
    python scripts/build_overlays.py airview_dublin path/to/AirView_DublinCity_RoadData_ugm3.shp
    python scripts/build_overlays.py airview_dublin path/to.shp --geojson out.geojson   # also a GeoJSON for GIS

The shapefile is read with the standard library only (polyline shapes), so no GIS
packages are needed here or on Vercel. A layer whose .prj is not WGS 84 is refused:
reproject it first (QGIS: Export → Save Features As…, CRS EPSG:4326).

Data rules (Google Air View road averages):
  * a pollutant with 0 measurement points (or an empty value) is "No data";
  * a negative value is a sensor error: it is excluded (kept as "No data", flagged);
  * values are rounded to 2 decimals, coordinates to 1e-5° (about 1 m).

Output, per layer: data/Overlays/<id>.json.gz, a compact column layout (a GeoJSON
FeatureCollection would be about 4× larger):
    { "id", "name", "kind": "lines", "bbox": [s, w, n, e], "count": N, "scale": 100000,
      "fields": [{"key", "label", "unit", "n", "excluded", "min", "max"}],
      "lookup": {"name": [...], "fclass": [...]},          # distinct strings
      "name": [i, ...], "fclass": [i, ...],                  # index into lookup, per feature
      "geom": [[[lat0, lng0, dlat, dlng, ...], ...], ...],   # per feature, per part: ints, delta-coded
      "values": {key: [v | null, ...]}, "points": {key: [...]}, "drives": {key: [...]},
      "errors": {key: [feature index, ...]} }               # negative values that were excluded
and data/Overlays/overlays.json, the catalogue the page lists (one entry per layer).
"""
from __future__ import annotations

import gzip
import json
import struct
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "data" / "Overlays"
CATALOG_PATH = OUT_DIR / "overlays.json"
SCALE = 100_000          # coordinates in 1e-5 degrees
TOLERANCE = 2e-5         # Douglas–Peucker, degrees (~1.5–2 m): drops only redundant vertices

# One entry per overlay layer. Add a layer here, run this script, and it appears in the page's list.
LAYERS = {
    "airview_dublin": {
        "source_shp": Path.home() / "Downloads" / "airview_dublincity_roaddata_ugm3" / "AirView_DublinCity_RoadData_ugm3.shp",
        "name": "Google Air View",
        "group": "Air Quality",
        "description": "Project Air View Dublin: street-level air quality measured every second by Google's electric "
                       "Street View car (Aclima sensors), May 2021 – Aug 2022, averaged over ~50 m road segments.",
        "credit": "Aclima & Google 2022 via Dublinked (CC BY 4.0)",
        "url": "https://data.gov.ie/dataset/google-airview-data-dublin-city/resource/ebee537f-2fc9-4576-8b74-728e5a430e08",
        "name_field": "osm_name",
        "class_field": "osm_fclass",
        "fields": [   # key, label, value field, points field, drives field, unit
            ("NO2",  "NO₂",   "NO2_ugm3",  "NO2points",  "NO2drives",  "µg/m³"),
            ("NO",   "NO",    "NO_ugm3",   "NOpoints",   "NOdrives",   "µg/m³"),
            ("PM25", "PM2.5", "PM25_ugm3", "PM25points", "PM25drives", "µg/m³"),
            ("O3",   "O₃",    "O3_ugm3",   "O3points",   "O3drives",   "µg/m³"),
            ("CO",   "CO",    "CO_mgm3",   "COpoints",   "COdrives",   "mg/m³"),
            ("CO2",  "CO₂",   "CO2_mgm3",  "CO2points",  "CO2drives",  "mg/m³"),
        ],
        "default_field": "NO2",
    },
}


# ---------------------------------------------------------------------------
# Shapefile reading (standard library)
# ---------------------------------------------------------------------------
def read_dbf(path: Path) -> list[dict]:
    d = path.read_bytes()
    n, header_len, rec_len = struct.unpack("<IHH", d[4:12])
    fields, p = [], 32
    while d[p] != 0x0D:
        fields.append((d[p:p + 11].split(b"\0")[0].decode(), d[p + 16]))
        p += 32
    rows = []
    for i in range(n):
        rec, o, row = d[header_len + i * rec_len + 1: header_len + (i + 1) * rec_len], 0, {}
        for name, length in fields:
            row[name] = rec[o:o + length].decode("utf-8", "replace").strip()
            o += length
        rows.append(row)
    return rows


def read_polylines(path: Path) -> list[list[list[tuple[float, float]]]]:
    """Every record as a list of parts, each a list of (x, y) = (lng, lat). Null shapes give []."""
    d = path.read_bytes()
    shape_type = struct.unpack("<i", d[32:36])[0]
    if shape_type not in (3, 13, 23):
        raise SystemExit(f"{path.name}: shape type {shape_type} is not a polyline (3 / 13 / 23).")
    out, p = [], 100
    while p + 8 <= len(d):
        content_len = struct.unpack(">i", d[p + 4:p + 8])[0] * 2
        rec = d[p + 8:p + 8 + content_len]
        p += 8 + content_len
        if struct.unpack("<i", rec[:4])[0] == 0:            # null shape
            out.append([])
            continue
        n_parts, n_points = struct.unpack("<ii", rec[36:44])
        starts = list(struct.unpack(f"<{n_parts}i", rec[44:44 + 4 * n_parts]))
        o = 44 + 4 * n_parts
        pts = [struct.unpack("<2d", rec[o + 16 * k:o + 16 * k + 16]) for k in range(n_points)]
        out.append([pts[a:b] for a, b in zip(starts, starts[1:] + [n_points])])
    return out


def check_wgs84(shp: Path) -> None:
    prj = shp.with_suffix(".prj")
    if not prj.exists():
        print(f"  warning: no {prj.name}; assuming WGS 84 longitude/latitude")
        return
    wkt = prj.read_text(errors="replace").upper()
    if wkt.startswith("PROJCS") or "WGS_1984" not in wkt.replace(" ", "_"):
        raise SystemExit(f"{shp.name} is not in WGS 84 (EPSG:4326). Reproject it first, then run this again.")


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------
def simplify(pts, tol):
    """Douglas–Peucker on (x, y) tuples; keeps the end points."""
    if len(pts) < 3:
        return pts
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        a, b = stack.pop()
        (x1, y1), (x2, y2) = pts[a], pts[b]
        dx, dy = x2 - x1, y2 - y1
        norm = (dx * dx + dy * dy) ** 0.5 or 1e-12
        best, idx = -1.0, -1
        for k in range(a + 1, b):
            x, y = pts[k]
            dist = abs(dy * (x - x1) - dx * (y - y1)) / norm
            if dist > best:
                best, idx = dist, k
        if best > tol:
            keep[idx] = True
            stack += [(a, idx), (idx, b)]
    return [q for q, k in zip(pts, keep) if k]


def encode_part(pts):
    """[(lng, lat), ...] -> [lat0, lng0, dlat, dlng, ...] in 1e-5 degrees (repeated points dropped)."""
    out, plat, plng = [], 0, 0
    for x, y in pts:
        lat, lng = round(y * SCALE), round(x * SCALE)
        if out and lat == plat and lng == plng:
            continue
        out += [lat - plat, lng - plng]
        plat, plng = lat, lng
    return out if len(out) >= 4 else None


def num(s: str):
    """A DBF numeric cell: None when empty or overflowed ('****')."""
    s = s.strip()
    if not s or s.startswith("*"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
def build(layer_id: str, cfg: dict, shp: Path, geojson_out: Path | None = None) -> dict:
    print(f"{layer_id}: reading {shp}")
    if not shp.exists():
        raise SystemExit(f"Shapefile not found: {shp}")
    check_wgs84(shp)
    rows, shapes = read_dbf(shp.with_suffix(".dbf")), read_polylines(shp)
    if len(rows) != len(shapes):
        raise SystemExit(f"{shp.name}: {len(shapes)} shapes but {len(rows)} attribute rows.")

    lookup = {"name": [], "fclass": []}
    index = {"name": {}, "fclass": {}}

    def ref(kind, s):
        if s not in index[kind]:
            index[kind][s] = len(lookup[kind])
            lookup[kind].append(s)
        return index[kind][s]

    keys = [f[0] for f in cfg["fields"]]
    cols = {"name": [], "fclass": [], "geom": []}
    values = {k: [] for k in keys}
    points = {k: [] for k in keys}
    drives = {k: [] for k in keys}
    errors = {k: [] for k in keys}
    s, n, w, e = 90.0, -90.0, 180.0, -180.0       # bounding box, grown by every vertex
    skipped = 0
    gj = [] if geojson_out else None

    for row, parts in zip(rows, shapes):
        geom = []
        for part in parts:
            enc = encode_part(simplify(part, TOLERANCE))
            if enc:
                geom.append(enc)
                for x, y in part:
                    s, n, w, e = min(s, y), max(n, y), min(w, x), max(e, x)
        if not geom:
            skipped += 1
            continue
        i = len(cols["geom"])
        cols["geom"].append(geom)
        cols["name"].append(ref("name", row.get(cfg["name_field"], "")))
        cols["fclass"].append(ref("fclass", row.get(cfg["class_field"], "")))
        props = {"name": row.get(cfg["name_field"], ""), "road_type": row.get(cfg["class_field"], "")}
        for key, _label, vf, pf, df, _unit in cfg["fields"]:
            v, pts_n, drv = num(row.get(vf, "")), num(row.get(pf, "")), num(row.get(df, ""))
            pts_n = int(pts_n or 0)
            drv = int(drv or 0) if pts_n else 0
            if pts_n == 0 or v is None:
                v = None
            elif v < 0:
                errors[key].append(i)
                v = None
            else:
                v = round(v, 2)
            values[key].append(v)
            points[key].append(pts_n)
            drives[key].append(drv)
            props[key] = v
            props[key + "_points"] = pts_n
        if gj is not None:
            gj.append({"type": "Feature", "properties": props, "geometry": {
                "type": "MultiLineString",
                "coordinates": [[[round(x, 5), round(y, 5)] for x, y in part] for part in parts if len(part) > 1]}})

    fields = []
    for key, label, *_rest, unit in cfg["fields"]:
        valid = [v for v in values[key] if v is not None]
        fields.append({"key": key, "label": label, "unit": unit, "n": len(valid), "excluded": len(errors[key]),
                       "min": min(valid) if valid else None, "max": max(valid) if valid else None})
        print(f"  {key:6} {len(valid):6} roads with data, {len(errors[key]):5} negative values excluded")

    data = {
        "id": layer_id, "name": cfg["name"], "kind": "lines",
        "bbox": [round(s, 5), round(w, 5), round(n, 5), round(e, 5)],
        "count": len(cols["geom"]), "scale": SCALE, "fields": fields,
        "lookup": lookup, **cols, "values": values, "points": points, "drives": drives, "errors": errors,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    out = OUT_DIR / f"{layer_id}.json.gz"
    out.write_bytes(gzip.compress(raw, 9, mtime=0))
    print(f"  {data['count']} roads ({skipped} empty shapes skipped); "
          f"{len(raw) / 1e6:.1f} MB JSON -> {out.relative_to(BASE_DIR)} {out.stat().st_size / 1e6:.2f} MB gzipped")

    if gj is not None:
        geojson_out.write_text(json.dumps({"type": "FeatureCollection", "features": gj}, ensure_ascii=False),
                               encoding="utf-8")
        print(f"  GeoJSON for GIS: {geojson_out}")

    return {"id": layer_id, "name": cfg["name"], "group": cfg["group"], "kind": "lines",
            "description": cfg["description"], "credit": cfg["credit"], "url": cfg["url"],
            "bbox": data["bbox"], "count": data["count"], "fields": fields,
            "default_field": cfg["default_field"], "file": out.name, "bytes": out.stat().st_size}


def main(argv):
    geojson = None
    if "--geojson" in argv:
        k = argv.index("--geojson")
        geojson = Path(argv[k + 1])
        argv = argv[:k] + argv[k + 2:]
    targets = {argv[0]: Path(argv[1]) if len(argv) > 1 else LAYERS[argv[0]]["source_shp"]} if argv \
        else {k: c["source_shp"] for k, c in LAYERS.items()}

    try:
        catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        catalog = {"layers": []}
    by_id = {l["id"]: l for l in catalog.get("layers", [])}
    for layer_id, shp in targets.items():
        if layer_id not in LAYERS:
            raise SystemExit(f"Unknown layer '{layer_id}'. Known: {', '.join(LAYERS)}")
        by_id[layer_id] = build(layer_id, LAYERS[layer_id], shp, geojson)
    catalog["layers"] = [by_id[k] for k in LAYERS if k in by_id]
    CATALOG_PATH.write_text(json.dumps(catalog, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Catalogue: {CATALOG_PATH.relative_to(BASE_DIR)} ({len(catalog['layers'])} layer(s))")


if __name__ == "__main__":
    main(sys.argv[1:])
