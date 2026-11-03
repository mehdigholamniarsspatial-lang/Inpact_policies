"""
Pack the PARIS inversion GeoTIFFs in InversionModel/ into grids the map can serve.

Why this exists
---------------
InversionModel/InversionModelGeotiff/ holds the annual CH4 and N2O fluxes of
three inversion systems (ELRIS, InTEM, RHIME) run with two transport models
(FLEXPART, NAME), written by InversionModel/Ireland_TopDown_BottomUp_GHG V1.ipynb
from the PARIS harmonised inversions (ICOS Carbon Portal, doi:10.18160/GR1Q-6SK4).
Reading them needs rasterio, which Vercel cannot install, so this script reads
them once on a local machine and writes, per inversion / transport / gas:

    data/InverseModel/<MODEL>_<TRANSPORT>_<GAS>.npz
        prior, posterior          (years, cells) kg km-2 yr-1
        prior_lo, prior_hi,       15.9th / 84.1st percentiles (1-sigma range)
        posterior_lo, posterior_hi

plus data/InverseModel/inverse_metadata.json: grid geometry, the country
fraction and cell area of every cell, years per run, colour-scale limits,
national totals and the uncertainty reduction ratio. explorer/inverse.py
serves these with numpy only.

Usage (from the project root, in an environment with rasterio installed):

    python scripts/build_inverse_grids.py
"""
import json
from pathlib import Path

import numpy as np
import rasterio

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "InversionModel" / "InversionModelGeotiff"
OUT_DIR = PROJECT_ROOT / "data" / "InverseModel"
TAG = "PARISNID2026"
UNITS = "kg_km2_yr"

MODELS = {
    "ELRIS": "Empa (Swiss Federal Laboratories for Materials Science and Technology)",
    "InTEM": "UK Met Office",
    "RHIME": "University of Bristol",
}
TRANSPORTS = {
    "FLEXPART": "FLEXible PARTicle dispersion model (Lagrangian)",
    "NAME": "Numerical Atmospheric-dispersion Modelling Environment (Met Office, Lagrangian)",
}
# The gas is not in the file names: the prior identifies it (notebook, Cell 18).
GASES = {
    "CH4": {"formula": "CH₄", "name": "Methane", "prior_tag": "EDGARWETCHARTS",
            "prior": "EDGAR v8 + WetCHARTs",
            "represents": "Total flux: anthropogenic plus natural wetland emissions. "
                          "Not directly comparable with the EPA inventory, which is "
                          "anthropogenic only (Irish peatlands make this a large term)."},
    "N2O": {"formula": "N₂O", "name": "Nitrous oxide", "prior_tag": "EDGAR",
            "prior": "EDGAR v8",
            "represents": "Total flux: anthropogenic plus natural soil and ocean emissions; "
                          "partly comparable with the EPA inventory."},
}
LAYERS = {
    "posterior": "flux_total_posterior",
    "prior": "flux_total_prior",
    "posterior_lo": "pctl0.159_posterior",
    "posterior_hi": "pctl0.841_posterior",
    "prior_lo": "pctl0.159_prior",
    "prior_hi": "pctl0.841_prior",
}


def _path(model, transport, gas, variable):
    run = f"{model}_{transport}_EUROPE_{GASES[gas]['prior_tag']}_{TAG}"
    suffix = variable if variable.startswith(("cell_area", "country_fraction")) else f"{variable}__{UNITS}"
    return SRC_DIR / f"{run}__{suffix}.tif"


def _read_annual(path):
    """Band years (from the band descriptions, ``None`` if absent) and (bands, cells) values."""
    with rasterio.open(path) as src:
        # InTEM_NAME N2O pctl0.159_prior carries its long_name instead of the
        # year in every band; its band count still matches the run's years.
        descriptions = [d or "" for d in src.descriptions]
        years = [int(d) for d in descriptions] if all(d.isdigit() for d in descriptions) else None
        return years, src.read().reshape(src.count, -1).astype("float32")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with rasterio.open(_path("ELRIS", "NAME", "CH4", "cell_area")) as src:
        t, rows, cols = src.transform, src.height, src.width
        area_km2 = (src.read(1).ravel() / 1e6)

    runs, fractions = {}, {}
    all_flux, all_diff = {g: [] for g in GASES}, {g: [] for g in GASES}
    for model in MODELS:
        # Each inversion system attributes cells to Ireland with its own mask
        # (ELRIS uses fractional coastal cells); it is the same for its runs.
        with rasterio.open(_path(model, "NAME", "CH4", "country_fraction_IRL")) as src:
            frac = np.nan_to_num(src.read(1)).ravel()
        fractions[model] = [round(float(v), 4) for v in frac]
        for transport in TRANSPORTS:
            for gas in GASES:
                arrays, years = {}, None
                for key, variable in LAYERS.items():
                    yrs, data = _read_annual(_path(model, transport, gas, variable))
                    if years is None:           # posterior comes first in LAYERS
                        years = yrs
                    assert years and (yrs or years) == years and len(data) == len(years), \
                        f"band years differ in {model} {transport} {gas} {variable}"
                    arrays[key] = data
                # Every file of a run must share the grid of the static layers.
                with rasterio.open(_path(model, transport, gas, "flux_total_posterior")) as src:
                    assert src.transform.almost_equals(t, precision=1e-6) and (src.height, src.width) == (rows, cols)
                np.savez_compressed(OUT_DIR / f"{model}_{transport}_{gas}.npz", **arrays)

                # Ireland total (Gg yr-1) = sum(F [kg km-2 yr-1] x A [km2] x f) / 1e6
                def total(a):
                    return [round(float(v), 3) for v in (a * area_km2 * frac).sum(axis=1) / 1e6]

                # Uncertainty reduction ratio: Ireland-weighted 1-sigma spread,
                # posterior / prior (notebook, Cell 16), from the annual percentiles.
                def spread(lo, hi):
                    return ((arrays[hi] - arrays[lo]) * frac).sum(axis=1) / frac.sum()

                urr = spread("posterior_lo", "posterior_hi") / spread("prior_lo", "prior_hi")
                runs[f"{model}|{transport}|{gas}"] = {
                    "years": years,
                    "total_prior": total(arrays["prior"]),
                    "total_posterior": total(arrays["posterior"]),
                    "urr": [round(float(v), 3) for v in urr],
                }
                # Scale limits come from the Ireland cells, so open sea does not
                # stretch the colour ramp.
                irl = frac > 0
                all_flux[gas] += [arrays["prior"][:, irl], arrays["posterior"][:, irl]]
                all_diff[gas].append((arrays["posterior"] - arrays["prior"])[:, irl])
                print(f"{model}-{transport} {gas}: {years[0]}-{years[-1]}, "
                      f"posterior {years[-1]} = {runs[f'{model}|{transport}|{gas}']['total_posterior'][-1]} Gg")

    # One fixed scale per gas across all runs and years, so maps compare directly.
    # The Ireland mask is mostly sea (fluxes ~1-100) while land cells reach
    # 1e3-1e4.6, so the log ramp spans three decades below P99.5: sea clamps
    # to the low end and the ramp resolves the land.
    scales = {}
    for gas in GASES:
        flux = np.concatenate([a.ravel() for a in all_flux[gas]])
        flux = flux[np.isfinite(flux) & (flux > 0)]
        diff = np.abs(np.concatenate([a.ravel() for a in all_diff[gas]]))
        hi = float(np.percentile(flux, 99.5))
        scales[gas] = {
            "flux": {"lo": max(float(np.percentile(flux, 1)), hi / 1e3), "hi": hi},
            "difference": {"limit": float(np.percentile(diff[np.isfinite(diff)], 99))},
        }

    meta = {
        "_about": "Written by scripts/build_inverse_grids.py from InversionModel/ "
                  "(see InversionModel/Ireland_TopDown_BottomUp_GHG V1.ipynb). Do not edit by hand.",
        "grid": {"west": t.c, "north": t.f, "dlon": t.a, "dlat": -t.e, "rows": rows, "cols": cols,
                 "crs": "EPSG:4326 (WGS 84)"},
        "country_fraction": fractions,
        "cell_area_km2": [round(float(v), 2) for v in area_km2],
        "models": MODELS,
        "transports": TRANSPORTS,
        "gases": {k: {kk: v for kk, v in g.items() if kk != "prior_tag"} for k, g in GASES.items()},
        "runs": runs,
        "scales": scales,
        "unit": "kg {gas} km⁻² yr⁻¹",
        "source": {
            "dataset": "PARIS harmonised inverse modelling results for European non-CO₂ GHG emissions",
            "credit": "Horizon Europe PARIS project, via ICOS Carbon Portal (CC BY 4.0)",
            "doi": "10.18160/GR1Q-6SK4",
            "url": "https://doi.org/10.18160/GR1Q-6SK4",
            "resolution": "0.352° × 0.234° (≈ 23 × 26 km, ≈ 600 km² per cell)",
            "coverage": "Ireland plus a 20 km buffer",
            "aggregation": "Day-weighted calendar-year mean of monthly fluxes",
            "uncertainty": "15.9th–84.1st percentiles (1σ-equivalent range)",
            "contact": "Dataset creators ask to be contacted before use in publications "
                       "(A. Manning, Met Office; S. Henne, Empa).",
            "notes": [
                "Cell-scale structure inside Ireland mostly reflects the prior, not the observations.",
                "The Ireland mask is the modellers' country_fraction (includes offshore cells), "
                "so totals reconcile with their published national figures.",
            ],
        },
    }
    (OUT_DIR / "inverse_metadata.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Wrote {len(runs)} runs and inverse_metadata.json to {OUT_DIR}")


if __name__ == "__main__":
    main()
