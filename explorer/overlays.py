"""
Vector overlay layers for the Spatial Environmental Mapping panel ("Air Quality"
button → Layer Overlay), e.g. the Google Air View Dublin road concentrations.

Each layer is packed offline by ``scripts/build_overlays.py`` into
``data/Overlays/<id>.json.gz`` (a compact column layout, gzipped), and listed in
``data/Overlays/overlays.json``. This module needs the standard library only.

The layer files are sent still gzipped (``Content-Encoding: gzip``), so a large
layer stays well under Vercel's 4.5 MB response limit and is never unpacked on
the server. The page classifies and colours the features itself.
"""
from __future__ import annotations

import gzip
import json
import re
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent
OVERLAY_DIR = BASE_DIR / "data" / "Overlays"
CATALOG_PATH = OVERLAY_DIR / "overlays.json"
_ID_RE = re.compile(r"^[a-z0-9_]{1,64}$")

_CACHE = {"mtime": None, "data": {"layers": []}}


def catalog() -> dict:
    """``overlays.json`` (re-read whenever it changes); an empty list when missing or broken."""
    try:
        mtime = CATALOG_PATH.stat().st_mtime
    except OSError:
        return {"layers": []}
    if _CACHE["mtime"] != mtime:
        try:
            data = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
            layers = [l for l in data.get("layers", []) if _ID_RE.match(str(l.get("id", "")))]
        except (ValueError, AttributeError):
            layers = []
        _CACHE.update(mtime=mtime, data={"layers": layers})
    return _CACHE["data"]


def layer_path(layer_id: str) -> Optional[Path]:
    """The packed file of a catalogued layer, or None (unknown id or missing file)."""
    if not _ID_RE.match(layer_id or ""):
        return None
    entry = next((l for l in catalog()["layers"] if l["id"] == layer_id), None)
    if entry is None:
        return None
    path = OVERLAY_DIR / entry.get("file", f"{layer_id}.json.gz")
    return path if path.is_file() and path.parent == OVERLAY_DIR else None


def read_layer(path: Path, gzip_ok: bool) -> bytes:
    """The layer body: the gzipped bytes as stored, or unpacked for a client that can't take gzip."""
    raw = path.read_bytes()
    return raw if gzip_ok else gzip.decompress(raw)
