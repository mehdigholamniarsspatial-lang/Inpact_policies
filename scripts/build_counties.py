"""
Build data/boundaries/counties.json from the county shapefile (OSM admin level 6).

Run once, offline, when the shapefile changes:
    python scripts/build_counties.py [path/to/AdminLevel6.shp]

The shapefile is read with the standard library only (polygon shapes, WGS 84),
so no GIS packages are needed. Rings are simplified (Douglas–Peucker), tiny
islands are dropped and coordinates are rounded, which keeps the file small
enough for the web map and the time series selection.

Output: {"counties": [{"name": "Cork", "bbox": [s, w, n, e], "rings": [[[lat, lng], ...], ...]}, ...]}
"""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_SHP = BASE_DIR.parent / "SHP" / "AdminLevel6.shp"
OUT_PATH = BASE_DIR / "data" / "boundaries" / "counties.json"
TOLERANCE = 0.002        # degrees (~150–220 m)
MIN_AREA = 2e-5          # square degrees; smaller islands are dropped
DIGITS = 4


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


def read_shp(path: Path) -> list[list[list[tuple[float, float]]]]:
    """Every record's rings as lists of (x, y)."""
    d, p, shapes = path.read_bytes(), 100, []
    while p < len(d):
        content_len = struct.unpack(">i", d[p + 4:p + 8])[0] * 2
        rec = d[p + 8:p + 8 + content_len]
        p += 8 + content_len
        if struct.unpack("<i", rec[:4])[0] != 5:
            shapes.append([])
            continue
        n_parts, n_pts = struct.unpack("<ii", rec[36:44])
        parts = list(struct.unpack(f"<{n_parts}i", rec[44:44 + 4 * n_parts])) + [n_pts]
        o = 44 + 4 * n_parts
        pts = [struct.unpack("<2d", rec[o + 16 * k:o + 16 * k + 16]) for k in range(n_pts)]
        shapes.append([pts[parts[i]:parts[i + 1]] for i in range(n_parts)])
    return shapes


def _seg_dist2(p, a, b) -> float:
    (px, py), (ax, ay), (bx, by) = p, a, b
    dx, dy = bx - ax, by - ay
    if dx == dy == 0:
        return (px - ax) ** 2 + (py - ay) ** 2
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return (px - ax - t * dx) ** 2 + (py - ay - t * dy) ** 2


def simplify(pts, tol: float):
    """Iterative Douglas–Peucker on an open polyline."""
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack, tol2 = [(0, len(pts) - 1)], tol * tol
    while stack:
        i, j = stack.pop()
        best, idx = 0.0, -1
        for k in range(i + 1, j):
            dd = _seg_dist2(pts[k], pts[i], pts[j])
            if dd > best:
                best, idx = dd, k
        if idx >= 0 and best > tol2:
            keep[idx] = True
            stack += [(i, idx), (idx, j)]
    return [p for p, k in zip(pts, keep) if k]


def area(ring) -> float:
    return abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1]))) / 2


def main(shp: Path) -> None:
    rows, shapes = read_dbf(shp.with_suffix(".dbf")), read_shp(shp)
    counties = []
    for row, rings in zip(rows, shapes):
        out = []
        for ring in rings:
            if area(ring) < MIN_AREA:
                continue
            # split the closed ring in two so the end points of both halves are kept
            half = len(ring) // 2
            s = simplify(ring[:half + 1], TOLERANCE)[:-1] + simplify(ring[half:], TOLERANCE)
            s = [(round(y, DIGITS), round(x, DIGITS)) for x, y in s]
            s = [p for i, p in enumerate(s) if i == 0 or p != s[i - 1]]
            if s and s[0] == s[-1]:
                s = s[:-1]
            if len(s) >= 3:
                out.append([list(p) for p in s])
        if not out:
            continue
        lats = [p[0] for r in out for p in r]
        lngs = [p[1] for r in out for p in r]
        name = row.get("name", "").removeprefix("County ").strip()
        counties.append({"name": name, "bbox": [min(lats), min(lngs), max(lats), max(lngs)], "rings": out})
    counties.sort(key=lambda c: c["name"])
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps({
        "source": "OpenStreetMap admin level 6 (counties of Ireland), simplified",
        "counties": counties,
    }, separators=(",", ":")), encoding="utf-8")
    n_pts = sum(len(r) for c in counties for r in c["rings"])
    print(f"{len(counties)} counties, {n_pts} points -> {OUT_PATH} ({OUT_PATH.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SHP)
