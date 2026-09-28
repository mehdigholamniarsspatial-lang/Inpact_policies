import csv

import pandas as pd
from django.conf import settings
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.cache import cache_page

from . import editorial, glossary, services
from . import models as m


def _base_context(active):
    return {"active": active, "glossary": glossary.as_payload()}


# ---------------------------------------------------------------- pages
def overview(request):
    ctx = _base_context("overview")
    ctx.update({
        "stats": services.overview_stats(),
        "matrix": services.sector_mechanism_matrix(),
        "materiality": m.SectorMateriality.objects.all(),
        "layers": [(k, *glossary.LAYERS[k]) for k in glossary.LAYER_ORDER],
        "emissions": services.emissions_context(),
        "emissions_source": editorial.EMISSIONS_SOURCE,
    })
    return render(request, "policies/overview.html", ctx)


def instruments(request):
    ctx = _base_context("instruments")
    series = list(m.PolicySeries.objects.exclude(layer="residual"))
    guide = []
    for key in glossary.MECHANISM_ORDER:
        if key == "mixed":
            continue
        info = editorial.INSTRUMENTS[key]
        members = sorted([x for x in series if x.mechanism == key], key=lambda x: (x.start_year, x.policy_name))
        seen, uniq = set(), []
        for x in members:
            if x.policy_id not in seen:
                seen.add(x.policy_id)
                uniq.append({"s": x, "sectors": sorted({y.sector for y in members if y.policy_id == x.policy_id})})
        guide.append({"key": key, "color": glossary.MECHANISMS[key][0], "label": glossary.MECHANISMS[key][1],
                      "info": info, "policies": uniq, "cmp": editorial.COMPARISON.get(key),
                      "refs": [editorial.LITERATURE[r] for r in info["refs"]]})
    ctx["guide"] = guide
    return render(request, "policies/instruments.html", ctx)


def about(request):
    ctx = _base_context("about")
    ctx["stats"] = services.overview_stats()
    ctx["literature"] = [editorial.LITERATURE[k] for k in (
        "NACHTIGALL2022", "KRUSE2022", "STECHEMESSER2024", "GOVREG", "IMPLREG", "OECDJRC2008", "IPCC2022", "EPA2026")]
    ctx["site"] = settings.SITE_INFO
    return render(request, "policies/about.html", ctx)


def timeline(request):
    return render(request, "policies/timeline.html", _base_context("timeline"))


def categories(request):
    ctx = _base_context("categories")
    ctx["mechanisms"] = [(k, *glossary.MECHANISMS[k]) for k in glossary.MECHANISM_ORDER]
    ctx["sectors"] = [(k, *glossary.SECTORS[k]) for k in glossary.SECTOR_ORDER]
    series = list(m.PolicySeries.objects.all())
    by_mech, by_sector = {}, {}
    for srs in series:
        by_mech.setdefault(srs.mechanism, []).append(srs)
        by_sector.setdefault(srs.sector, []).append(srs)
    ctx["mechanism_groups"] = [
        {"key": k, "color": c, "label": lab, "desc": d,
         "items": sorted(by_mech.get(k, []), key=lambda x: (x.start_year, x.policy_name))}
        for k, c, lab, d in ctx["mechanisms"] if by_mech.get(k)]
    emis = {e["sector"]: e for e in services.emissions_context()}
    ctx["sector_groups"] = [
        {"key": k, "color": c, "label": k, "desc": d, "emis": emis.get(k),
         "items": sorted(by_sector.get(k, []), key=lambda x: (x.start_year, x.policy_name))}
        for k, c, d in ctx["sectors"] if by_sector.get(k)]
    ctx["coverage_scores"] = sorted(glossary.COVERAGE_SCORES.items(), reverse=True)
    ctx["binding_scores"] = sorted(glossary.BINDINGNESS_SCORES.items(), reverse=True)
    return render(request, "policies/categories.html", ctx)


def explorer(request):
    return render(request, "policies/explorer.html", _base_context("explorer"))


def policy_detail(request, slug):
    series = get_object_or_404(m.PolicySeries, slug=slug)
    ctx = _base_context("explorer")
    ctx["s"] = series
    ctx["d"] = services.policy_detail(series)
    ctx["layer_info"] = glossary.LAYERS.get(series.layer)
    ctx["mech_info"] = glossary.MECHANISMS.get(series.mechanism)
    ctx["match_info"] = glossary.MATCH_CONFIDENCE.get(series.match_confidence)
    ctx["selection_info"] = glossary.SELECTION_RULE.get(series.selection_rule)
    ctx["source_info"] = glossary.SOURCE_DATASETS.get(series.source_datasets)
    ctx["aggregation_info"] = glossary.AGGREGATION_ROLE.get(series.aggregation_role, "")
    ctx["coverage_label"] = glossary.COVERAGE_SCORES.get(series.coverage_share, "")
    ctx["binding_label"] = glossary.BINDINGNESS_SCORES.get(series.bindingness, "")
    ctx["sector_color"] = glossary.SECTORS.get(series.sector, ("#777", ""))[0]
    return render(request, "policies/policy_detail.html", ctx)


def capmf(request):
    ctx = _base_context("capmf")
    ctx["level3_count"] = m.CapmfCategory.objects.filter(level=3).count()
    ctx["level4_count"] = m.CapmfCategory.objects.filter(level=4).count()
    return render(request, "policies/capmf.html", ctx)


def method(request):
    ctx = _base_context("method")
    ctx.update({
        "stats": services.overview_stats(),
        "materiality": m.SectorMateriality.objects.all(),
        "checks": [{"title": editorial.VALIDATION.get(c.check_name, (c.check_name, c.detail))[0],
                    "detail": editorial.VALIDATION.get(c.check_name, (c.check_name, c.detail))[1],
                    "result": c.result} for c in m.ValidationCheck.objects.all()],
        "decisions": editorial.METHOD_DECISIONS,
        "references": m.Reference.objects.all(),
        "dictionary": m.DictionaryField.objects.all(),
        "overlaps": m.OverlapRelation.objects.all(),
        "timing": _timing_parameters(),
        "materiality_json": [
            {"sector": x.sector, "share": x.achieved_share, "units": x.materiality_units,
             "eligible": x.eligible_pam_units, "total": x.ranking_total_kt, "selected": x.selected_ranking_kt,
             "assessment": x.assessment} for x in m.SectorMateriality.objects.all()],
        "flow": {
            "eea_records": m.EeaPam.objects.count(),
            "eea_single": m.EeaPam.objects.exclude(policy_id="").count(),
            "eea_units": m.SelectionCandidate.objects.filter(candidate_origin="EEA_deduplicated_PaM").count(),
            "capmf_l3": m.CapmfCategory.objects.filter(level=3).count(),
            "capmf_pos": m.SelectionCandidate.objects.filter(candidate_origin="CAPMF_positive_LEV3").count(),
            "eea_core": m.SelectionCandidate.objects.filter(candidate_origin="EEA_deduplicated_PaM", outcome="core").count(),
            "eea_residual": m.SelectionCandidate.objects.filter(outcome="residual").count(),
            "eea_excluded": m.SelectionCandidate.objects.filter(candidate_origin="EEA_deduplicated_PaM", outcome="excluded").count(),
            "capmf_core": m.SelectionCandidate.objects.filter(candidate_origin="CAPMF_positive_LEV3", outcome="core").count(),
            "capmf_excluded": m.SelectionCandidate.objects.filter(candidate_origin="CAPMF_positive_LEV3", outcome="excluded").count(),
            "core_families": m.PolicySeries.objects.exclude(layer="residual").values("policy_id").distinct().count(),
            "residual_bundles": m.PolicySeries.objects.filter(layer="residual").count(),
        },
    })
    return render(request, "policies/method.html", ctx)


def _timing_parameters():
    path = settings.POLICY_DATA_DIR / "config" / "timing_parameters.csv"
    if not path.exists():
        return []
    df = pd.read_csv(path)
    df["parameter_basis"] = df["parameter_basis"].map(editorial.clean_text)
    return df.to_dict("records")


# ---------------------------------------------------------------- JSON API
@cache_page(60 * 10)
def api_series(request):
    return JsonResponse({"years": services.YEARS, "series": services.series_payload()})


@cache_page(60 * 10)
def api_capmf(request):
    level = int(request.GET.get("level", 3))
    if level not in (1, 2, 3, 4):
        raise Http404
    return JsonResponse({"level": level, "categories": services.capmf_payload(level)})


def api_selection(request):
    rows = list(m.SelectionCandidate.objects.values(
        "candidate_id", "candidate_origin", "candidate_name", "eligible", "exclusion_reason",
        "selection_rule", "primary_sector", "reported_effect_kt", "cumulative_effect_share",
        "sector_effect_rank", "output_policy_ids", "outcome", "anchor_flag", "materiality_group_flag",
        "criteria_a_mitigation", "criteria_b_ireland", "criteria_c_instrument", "criteria_d_start",
        "criteria_e_active"))
    return JsonResponse({"candidates": rows})


def api_year_snapshot(request, year):
    if year < 2000 or year > 2023:
        raise Http404
    rows = m.PolicyYear.objects.filter(year=year).select_related("series")
    data = [{"slug": r.series.slug, "name": r.series.policy_name, "sector": r.series.sector,
             "mechanism": r.series.mechanism, "layer": r.series.layer, "status": r.status_in_year,
             "intensity": r.intensity_index, "impl": r.implementation_level,
             "capmf": r.capmf_stringency, "source": r.implementation_source} for r in rows]
    return JsonResponse({"year": year, "rows": data})


# ---------------------------------------------------------------- CSV export
def export_csv(request):
    """Download the original release rows, filtered by the dashboard's selections."""
    df = pd.read_csv(settings.POLICY_DATA_DIR / "ireland_core_policy_timeline.csv", dtype=str, keep_default_na=False)
    for param, col in [("sector", "sector"), ("layer", "layer"), ("mechanism", "mechanism"),
                       ("policy_id", "policy_id"), ("source", "source_datasets")]:
        vals = [v for v in request.GET.getlist(param) if v]
        if vals:
            df = df[df[col].isin(vals)]
    y0, y1 = request.GET.get("from"), request.GET.get("to")
    if y0:
        df = df[df["year"].astype(int) >= int(y0)]
    if y1:
        df = df[df["year"].astype(int) <= int(y1)]
    for col in ["start_year_basis", "coverage_rationale", "bindingness_rationale", "parameter_basis", "implementation_detail"]:
        df[col] = df[col].map(editorial.clean_text)
    df["source_citation"] = df["source_citation"].map(lambda v: " | ".join(editorial.format_citations(v)))
    df = df.rename(columns=editorial.COLUMN_RENAMES)
    resp = HttpResponse(content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = 'attachment; filename="ireland_climate_policy_timeline_2000_2023.csv"'
    df.to_csv(resp, index=False, quoting=csv.QUOTE_MINIMAL)
    return resp
