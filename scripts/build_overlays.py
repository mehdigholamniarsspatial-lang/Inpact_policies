"""
Build the vector overlay layers of the Spatial Environmental Mapping panel
("Air Quality" button → Layer Overlay) from their source shapefiles.

Sources: a polyline shapefile (Google Air View roads) or a GeoPackage layer of points,
lines and/or polygons (health locations). Only the attribute fields named in LAYERS
are kept, so the packed files stay small.

Run once, offline, when a source changes:
    python scripts/build_overlays.py                         # every layer in LAYERS
    python scripts/build_overlays.py airview_dublin path/to/AirView_DublinCity_RoadData_ugm3.shp
    python scripts/build_overlays.py airview_dublin path/to.shp --geojson out.geojson   # also a GeoJSON for GIS
    python scripts/build_overlays.py hse_health_centres                                 # one GeoPackage layer

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

GeoPackage layers (kind "point", "polygon" or "mixed") use a feature layout instead:
    { "id", "name", "kind", "bbox", "count", "scale",
      "gtype": [1 | 2 | 3, ...],                 # mixed layers only: point / line / polygon, per feature
      "geom": [...],                             # point: [lat, lng] ints; line: [part, ...];
                                                 # polygon: [[ring, ...], ...] (one list of rings per polygon),
                                                 # parts and rings delta-coded as for the roads
      "fields": [{"key", "label", "type": "category" | "text", "values": [...], "counts": [...]}],
      "attrs": {key: [index into values | -1 (not recorded), ...] or [text | null, ...]} }
"""
from __future__ import annotations

import gzip
import json
import sqlite3
import struct
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "data" / "Overlays"
CATALOG_PATH = OUT_DIR / "overlays.json"
SCALE = 100_000          # coordinates in 1e-5 degrees
TOLERANCE = 2e-5         # Douglas–Peucker, degrees (~1.5–2 m): drops only redundant vertices
POLY_TOLERANCE = 1e-5    # building / site outlines: about 1 m
HEALTH_DIR = Path(r"C:\MyDriveD\INPACT Project\Dataset\ireland_health_locations")
OSM_CREDIT = "© OpenStreetMap contributors (ODbL 1.0), extract of 20 Nov 2026"

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
    # ---- Health locations (GeoPackage layers; only the listed fields are kept) ----
    "hse_health_centres": {
        "format": "gpkg", "source": HEALTH_DIR / "hse_health_centres.gpkg", "table": "health_centres",
        "name": "HSE health centres",
        "group": "Health locations",
        "description": "Health centres (GP and nurse services) listed by the HSE, hosted by the Heritage Council.",
        "credit": "Heritage Council Health Centres layer (references HSE), last edited 28 Jan 2025",
        "url": "https://www.arcgis.com/home/item.html?id=5993f5720d1a4fd6be1da191fd092445",
        "fields": [   # key, label, source column, type ("text": a name per feature; "category": a few values)
            ("service_name", "Service name", "Service_name", "text"),
            ("county", "County", "County", "category"),
        ],
        "default_field": "county",
    },
    "osm_health_polygons": {
        "format": "gpkg", "source": HEALTH_DIR / "osm_health_facilities.gpkg", "table": "facility_polygons",
        "name": "OSM health facility footprints",
        "group": "Health locations",
        "description": "Mapped building and site outlines of hospitals, clinics, doctors, dentists and pharmacies.",
        "credit": OSM_CREDIT,
        "url": "https://www.openstreetmap.org/copyright",
        "fields": [("amenity", "Amenity", "amenity", "category")],
        "default_field": "amenity",
    },
    "osm_health_facilities": {
        "format": "gpkg", "source": HEALTH_DIR / "osm_health_facilities.gpkg", "table": "facilities",
        "name": "OSM health facilities",
        "group": "Health locations",
        "description": "Every selected OSM healthcare feature as mapped: points, building outlines and a few lines.",
        "credit": OSM_CREDIT,
        "url": "https://www.openstreetmap.org/copyright",
        "fields": [
            ("amenity", "Amenity", "amenity", "category"),
            ("dispensing", "Dispensing", "dispensing", "category"),
            ("drive_through", "Drive-through", "drive_through", "category"),
        ],
        "default_field": "amenity",
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
# GeoPackage reading (standard library: a GeoPackage is SQLite, geometries are GP header + WKB)
# ---------------------------------------------------------------------------
def parse_gpkg_geom(blob: bytes):
    """GeoPackage geometry blob -> (kind, coords): ("point", (x, y)), ("line", [parts]),
    ("polygon", [[rings], ...]) or (None, None) for an empty geometry. x = lng, y = lat."""
    if not blob or blob[:2] != b"GP":
        return None, None
    flags = blob[3]
    if flags & 0x10:                                        # empty geometry flag
        return None, None
    env = (flags >> 1) & 7
    off = 8 + {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}[env]
    geoms, _ = _wkb(blob, off)
    pts = [g for k, g in geoms if k == "point"]
    lines = [g for k, g in geoms if k == "line"]
    polys = [g for k, g in geoms if k == "polygon"]
    if polys:
        return "polygon", polys
    if lines:
        return "line", lines
    if pts:
        return "point", pts[0]
    return None, None


def _wkb(b: bytes, o: int):
    """One WKB geometry at offset o -> ([(kind, coords), ...], next offset). Z / M values are dropped."""
    bo = "<" if b[o] == 1 else ">"
    t = struct.unpack(bo + "I", b[o + 1:o + 5])[0]
    o += 5
    has_z = bool(t & 0x80000000) or (t % 10000) // 1000 in (1, 3)
    has_m = bool(t & 0x40000000) or (t % 10000) // 1000 in (2, 3)
    base = (t & 0x0FFFFFFF) % 1000
    dim = 2 + has_z + has_m
    step = 8 * dim

    def coords(o, n):
        return [struct.unpack(bo + "2d", b[o + i * step:o + i * step + 16]) for i in range(n)], o + n * step

    if base == 1:
        (x, y), o = coords(o, 1)[0][0], o + step
        return ([] if x != x else [("point", (x, y))]), o          # NaN: empty point
    if base == 2:
        n = struct.unpack(bo + "I", b[o:o + 4])[0]
        pts, o = coords(o + 4, n)
        return [("line", pts)], o
    if base == 3:
        nr = struct.unpack(bo + "I", b[o:o + 4])[0]
        o += 4
        rings = []
        for _ in range(nr):
            n = struct.unpack(bo + "I", b[o:o + 4])[0]
            pts, o = coords(o + 4, n)
            rings.append(pts)
        return [("polygon", rings)], o
    if base in (4, 5, 6, 7):                                  # multi* and geometry collections
        n = struct.unpack(bo + "I", b[o:o + 4])[0]
        o += 4
        out = []
        for _ in range(n):
            g, o = _wkb(b, o)
            out += g
        return out, o
    raise ValueError(f"unsupported WKB geometry type {t}")


def encode_ring(pts, tol):
    """A polygon ring: simplified, closing vertex dropped (Leaflet closes rings), delta-coded."""
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts = pts[:-1]
    if len(pts) > 3:
        closed = simplify(pts + [pts[0]], tol)[:-1]
        if len(closed) >= 3:
            pts = closed
    enc = encode_part(pts)
    return enc if enc and len(enc) >= 6 else None


def simplify_line(pts, tol):
    """Douglas–Peucker for a line that may be closed (a ring drawn as a line): a closed line is
    simplified open, then closed again, so it does not collapse to its end points."""
    if len(pts) > 3 and pts[0] == pts[-1]:
        return simplify(pts[:-1], tol) + [pts[0]]
    return simplify(pts, tol)


def build_gpkg(layer_id: str, cfg: dict, src: Path) -> dict:
    print(f"{layer_id}: reading {src} (layer {cfg['table']})")
    if not src.exists():
        raise SystemExit(f"GeoPackage not found: {src}")
    con = sqlite3.connect(f"file:{src.as_posix()}?mode=ro", uri=True)
    try:
        row = con.execute("SELECT column_name, srs_id FROM gpkg_geometry_columns WHERE table_name = ?",
                          (cfg["table"],)).fetchone()
        if not row:
            raise SystemExit(f"{src.name}: no layer '{cfg['table']}'.")
        geom_col, srs = row
        org = con.execute("SELECT organization, organization_coordsys_id FROM gpkg_spatial_ref_sys WHERE srs_id = ?",
                          (srs,)).fetchone()
        if not org or (str(org[0]).upper(), int(org[1])) != ("EPSG", 4326):
            raise SystemExit(f"{src.name}:{cfg['table']} is not in WGS 84 (EPSG:4326). Reproject it first.")
        cols = [c for _k, _l, c, _t in cfg["fields"]]
        sel = ", ".join(f'"{c}"' for c in [geom_col] + cols)
        rows = con.execute(f'SELECT {sel} FROM "{cfg["table"]}" ORDER BY fid').fetchall()
    finally:
        con.close()

    keys = [f[0] for f in cfg["fields"]]
    types = {k: t for k, _l, _c, t in cfg["fields"]}
    attrs = {k: [] for k in keys}
    values = {k: [] for k in keys if types[k] == "category"}
    index = {k: {} for k in values}
    geom, gtype = [], []
    s, n, w, e = 90.0, -90.0, 180.0, -180.0
    skipped = 0
    GT = {"point": 1, "line": 2, "polygon": 3}

    for r in rows:
        kind, c = parse_gpkg_geom(r[0])
        if kind == "point":
            enc = [round(c[1] * SCALE), round(c[0] * SCALE)]
            verts = [c]
        elif kind == "line":
            enc = [p for p in (encode_part(simplify_line(part, POLY_TOLERANCE)) for part in c) if p]
            verts = [v for part in c for v in part]
        elif kind == "polygon":
            enc = []
            for poly in c:
                rings = [q for q in (encode_ring(ring, POLY_TOLERANCE) for ring in poly) if q]
                if rings:
                    enc.append(rings)
            verts = [v for poly in c for v in poly[0]]
        else:
            enc = None
        if not enc:
            skipped += 1
            continue
        for x, y in verts:
            s, n, w, e = min(s, y), max(n, y), min(w, x), max(e, x)
        geom.append(enc)
        gtype.append(GT[kind])
        for k, v in zip(keys, r[1:]):
            v = str(v).strip() if v is not None else ""
            if types[k] == "text":
                attrs[k].append(v or None)
            elif not v:
                attrs[k].append(-1)                              # not recorded
            else:
                if v not in index[k]:
                    index[k][v] = len(values[k])
                    values[k].append(v)
                attrs[k].append(index[k][v])

    kinds = sorted(set(gtype))
    layer_kind = {(1,): "point", (3,): "polygon", (2,): "line"}.get(tuple(kinds), "mixed")
    fields = []
    for k, label, _c, t in cfg["fields"]:
        f = {"key": k, "label": label, "type": t, "n": sum(1 for v in attrs[k] if v is not None and v != -1)}
        if t == "category":
            f["values"] = values[k]
            f["counts"] = [attrs[k].count(i) for i in range(len(values[k]))]
            f["missing"] = attrs[k].count(-1)
        fields.append(f)
        print(f"  {k:14} {f['n']:6} recorded" + (f", {len(values[k])} distinct values" if t == "category" else ""))

    data = {"id": layer_id, "name": cfg["name"], "kind": layer_kind,
            "bbox": [round(s, 5), round(w, 5), round(n, 5), round(e, 5)],
            "count": len(geom), "scale": SCALE, "fields": fields, "geom": geom, "attrs": attrs}
    if layer_kind == "mixed":
        data["gtype"] = gtype
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    out = OUT_DIR / f"{layer_id}.json.gz"
    out.write_bytes(gzip.compress(raw, 9, mtime=0))
    counts = {k: gtype.count(v) for k, v in GT.items() if gtype.count(v)}
    print(f"  {data['count']} features {counts} ({skipped} empty skipped); "
          f"{len(raw) / 1e3:.0f} kB JSON -> {out.relative_to(BASE_DIR)} {out.stat().st_size / 1e3:.0f} kB gzipped")
    return {"id": layer_id, "name": cfg["name"], "group": cfg["group"], "kind": layer_kind,
            "description": cfg["description"], "credit": cfg["credit"], "url": cfg["url"],
            "bbox": data["bbox"], "count": data["count"], "geometry": counts,
            "fields": [{k: v for k, v in f.items() if k not in ("values", "counts")} for f in fields],
            "default_field": cfg["default_field"], "file": out.name, "bytes": out.stat().st_size}


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
    src = lambda c: c.get("source_shp") or c["source"]
    targets = {argv[0]: Path(argv[1]) if len(argv) > 1 else src(LAYERS[argv[0]])} if argv \
        else {k: src(c) for k, c in LAYERS.items()}

    try:
        catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        catalog = {"layers": []}
    by_id = {l["id"]: l for l in catalog.get("layers", [])}
    for layer_id, shp in targets.items():
        if layer_id not in LAYERS:
            raise SystemExit(f"Unknown layer '{layer_id}'. Known: {', '.join(LAYERS)}")
        cfg = LAYERS[layer_id]
        by_id[layer_id] = build_gpkg(layer_id, cfg, shp) if cfg.get("format") == "gpkg" \
            else build(layer_id, cfg, shp, geojson)
    catalog["layers"] = [by_id[k] for k in LAYERS if k in by_id]
    CATALOG_PATH.write_text(json.dumps(catalog, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Catalogue: {CATALOG_PATH.relative_to(BASE_DIR)} ({len(catalog['layers'])} layer(s))")


if __name__ == "__main__":
    main(sys.argv[1:])
