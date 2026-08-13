"""
Pre-render every raster in data/Raster to a web-ready PNG + metadata JSON.

Why this exists
---------------
Rendering a .tif overlay requires rasterio/GDAL (the source grids are in Irish
Grid EPSG:29902 and must be reprojected to Web-Mercator). Those native
libraries cannot be installed on Vercel's Python serverless runtime, so the
live /api/raster/... endpoints cannot render there.

Instead, run THIS script on your local machine (where rasterio works) after
adding or changing any .tif in data/Raster. It writes, for every raster:

    data/RasterPrerendered/<stem>.png    the RGBA overlay image
    data/RasterPrerendered/<stem>.json   bounds / vmin / vmax / stops / ...

Commit data/RasterPrerendered/ to Git and push. On Vercel, explorer/rasters.py
detects that rasterio is missing and serves these pre-rendered files instead,
so the overlays work identically to your local machine.

Usage (from the project root, in an environment with rasterio installed):

    python scripts/prerender_rasters.py
"""
import base64
import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RASTER_DIR = PROJECT_ROOT / "data" / "Raster"
OUTPUT_DIR = PROJECT_ROOT / "data" / "RasterPrerendered"
FORCE = False  # True = re-render everything even if the output looks up to date

sys.path.insert(0, str(PROJECT_ROOT))

from explorer import rasters  # noqa: E402  (needs PROJECT_ROOT on sys.path)

if not rasters.RASTERIO_AVAILABLE:
    sys.exit(
        "rasterio is not installed in this environment. Install it first:\n"
        '    pip install "rasterio>=1.3,<2"'
    )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    catalog = rasters.scan_catalog()
    if not catalog:
        sys.exit(f"No rasters found in {RASTER_DIR}")

    n_done = n_skipped = 0
    for year, sectors in sorted(catalog.items()):
        for sector, params in sorted(sectors.items()):
            for parameter, filename in sorted(params.items()):
                src = RASTER_DIR / filename
                stem = Path(filename).stem
                png_out = OUTPUT_DIR / f"{stem}.png"
                meta_out = OUTPUT_DIR / f"{stem}.json"

                # Skip if outputs exist and are newer than the source .tif.
                if (
                    not FORCE
                    and png_out.is_file()
                    and meta_out.is_file()
                    and png_out.stat().st_mtime >= src.stat().st_mtime
                ):
                    n_skipped += 1
                    continue

                r = rasters._render(src)
                png_out.write_bytes(r["png"])
                meta = {k: v for k, v in r.items() if k != "png"}
                # Some values can be numpy scalars (e.g. the float32 tiny-value
                # fallback for vmin); coerce everything to plain Python types.
                meta_out.write_text(
                    json.dumps(meta, default=float), encoding="utf-8"
                )
                n_done += 1
                print(f"rendered  {filename}  ->  {png_out.name} ({len(r['png'])/1024:.1f} kB)")

    print(f"\nDone: {n_done} rendered, {n_skipped} already up to date.")
    print(f"Output: {OUTPUT_DIR}")
    print("Remember to `git add data/RasterPrerendered` and push before redeploying.")


if __name__ == "__main__":
    main()
