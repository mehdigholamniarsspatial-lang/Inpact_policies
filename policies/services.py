"""Query helpers that turn database rows into compact JSON-ready structures."""
from collections import Counter, defaultdict

from django.db.models import Prefetch

from . import editorial, glossary
from . import models as m

YEARS = list(range(2000, 2024))


def _r(v, n=4):
    return None if v is None else round(v, n)


def series_payload():
    """All 47 policy-sector series with their 24-year arrays."""
    qs = m.PolicySeries.objects.prefetch_related(
        Prefetch("years", queryset=m.PolicyYear.objects.order_by("year")))
    out = []
    for s in qs:
        ys = list(s.years.all())
        out.append({
            "slug": s.slug,
            "id": s.policy_id,
            "name": s.policy_name,
            "sector": s.sector,
            "layer": s.layer,
            "bundle": s.bundle,
            "mechanism": s.mechanism,
            "regime": s.regime,
            "instrument": s.instrument_type,
            "ghg": s.ghg_affected,
            "source": s.source_datasets,
            "match": s.match_confidence,
            "selection": s.selection_rule,
            "anchor": s.anchor_flag,
            "materiality": s.materiality_group_flag,
            "multiSector": s.multi_sector_flag,
            "start": s.start_year,
            "end": s.end_year,
            "effectKt": _r(s.reported_effect_kt, 1),
            "effectSource": s.effect_source,
            "coverage": s.coverage_share,
            "bindingness": s.bindingness,
            "capmfCode": s.capmf_code,
            "aggregation": s.aggregation_role,
            "legacy": s.legacy,
            "peak": _r(s.peak_intensity),
            "i2023": _r(s.intensity_2023),
            "capmfYears": s.capmf_years,
            "assumedYears": s.assumed_years,
            "summary": (s.description or "")[:260],
            "years": {
                "status": [y.status_in_year for y in ys],
                "impl": [_r(y.implementation_level) for y in ys],
                "capmf": [_r(y.capmf_stringency, 3) for y in ys],
                "intensity": [_r(y.intensity_index) for y in ys],
                "gated": [_r(y.intensity_index_equal_gated) for y in ys],
                "src": [y.implementation_source for y in ys],
            },
        })
    return out


def overview_stats():
    series = m.PolicySeries.objects.all()
    core_ids = {s.policy_id for s in series if s.layer != "residual"}
    cands = m.SelectionCandidate.objects.all()
    outcome = Counter(c.outcome for c in cands)
    origin_outcome = Counter((c.candidate_origin, c.outcome) for c in cands)
    active_2023 = m.PolicyYear.objects.filter(year=2023, status_in_year="active").count()
    active_2000 = m.PolicyYear.objects.filter(year=2000, status_in_year="active").count()
    by_source = Counter()
    seen = set()
    for s in series:
        if s.policy_id in seen:
            continue
        seen.add(s.policy_id)
        by_source[s.source_datasets] += 1
    return {
        "core_families": len(core_ids),
        "residual_bundles": series.filter(layer="residual").count(),
        "series": series.count(),
        "rows": m.PolicyYear.objects.count(),
        "years": f"{YEARS[0]}\u2013{YEARS[-1]}",
        "candidates": cands.count(),
        "eligible": sum(1 for c in cands if c.eligible),
        "outcome": dict(outcome),
        "origin_outcome": {f"{k[0]}|{k[1]}": v for k, v in origin_outcome.items()},
        "eea_records": m.EeaPam.objects.count(),
        "eea_single": m.EeaPam.objects.exclude(policy_id="").count(),
        "eea_groups": m.EeaPam.objects.filter(policy_id="").count(),
        "capmf_categories": m.CapmfCategory.objects.filter(level=3).count(),
        "capmf_indicators": m.CapmfCategory.objects.filter(level=4).count(),
        "active_2023": active_2023,
        "active_2000": active_2000,
        "by_source": dict(by_source),
        "checks_passed": m.ValidationCheck.objects.filter(result="PASS").count(),
        "checks_total": m.ValidationCheck.objects.count(),
    }


def sector_mechanism_matrix():
    """Count of policy-sector series by sector and mechanism (core + residual)."""
    counts = defaultdict(lambda: defaultdict(list))
    for s in m.PolicySeries.objects.all():
        counts[s.sector][s.mechanism].append({"name": s.policy_name, "slug": s.slug})
    return {sec: dict(mech) for sec, mech in counts.items()}


def capmf_payload(level=3):
    cats = m.CapmfCategory.objects.filter(level=level).prefetch_related(
        Prefetch("observations", queryset=m.CapmfObservation.objects.filter(measure="POL_STRINGENCY").order_by("year")))
    used = defaultdict(list)
    for s in m.PolicySeries.objects.exclude(capmf_code=""):
        for code in s.capmf_code.split(";"):
            used[code.strip()].append({"name": s.policy_name, "slug": s.slug, "sector": s.sector})
    out = []
    for c in cats:
        obs = {o.year: o for o in c.observations.all()}
        years = sorted(obs)
        linked = list(used.get(c.code, []))
        # LEV4 children link up to their LEV3 parent in the dashboard
        out.append({
            "code": c.code,
            "label": c.label,
            "domain": c.domain or "Other",
            "cls": c.instrument_class or "",
            "firstPositive": c.first_positive_year,
            "eligible": c.eligible,
            "exclusion": c.exclusion_reason,
            "representedBy": c.represented_by,
            "years": years,
            "values": [_r(obs[y].value, 3) for y in years],
            "status": [obs[y].status for y in years],
            "linked": linked,
        })
    return out


def policy_detail(series):
    years = list(series.years.order_by("year"))
    siblings = m.PolicySeries.objects.filter(policy_id=series.policy_id).exclude(pk=series.pk)
    pam_ids = [p.strip() for p in (series.all_eea_variant_ids or "").split(";") if p.strip().isdigit()]
    pams = m.EeaPam.objects.filter(pam_id__in=[int(p) for p in pam_ids])
    overlaps = m.OverlapRelation.objects.filter(parent_id=series.policy_id) | \
        m.OverlapRelation.objects.filter(related_id=series.policy_id)
    ov = []
    names = {s.policy_id: (s.policy_name, s.slug) for s in m.PolicySeries.objects.all()}
    for o in overlaps:
        other = o.related_id if o.parent_id == series.policy_id else o.parent_id
        role = "child or component" if o.parent_id == series.policy_id else "parent or context"
        nm, slug = names.get(other, (other, None))
        ov.append({"other": nm, "slug": slug, "relationship": glossary.humanise(o.relationship),
                   "role": role, "treatment": o.treatment})
    members = []
    if series.layer == "residual":
        members = list(m.ResidualMember.objects.filter(residual_sector=series.sector).order_by("start_year"))
    flags = [f for f in series.data_quality_flags.split(";") if f]
    grouped = defaultdict(list)
    for f in flags:
        grouped[glossary.flag_group(f)].append(editorial.FLAG_TEXT.get(f, glossary.humanise(f) + "."))
    capmf_codes = [c.strip() for c in series.capmf_code.split(";") if c.strip()]
    capmf_labels = {c.code: c.label for c in m.CapmfCategory.objects.filter(code__in=capmf_codes)}
    citations = [c.strip() for c in (series.source_citation or "").split("\n") if c.strip()]
    instrument = editorial.INSTRUMENTS.get(series.mechanism)
    milestones = editorial.POLICY_MILESTONES.get(series.policy_id, [])
    return {
        "years": years,
        "siblings": siblings,
        "pams": pams,
        "overlaps": ov,
        "members": members,
        "flag_groups": dict(grouped),
        "capmf": [(c, capmf_labels.get(c, "")) for c in capmf_codes],
        "citations": citations,
        "instrument": instrument,
        "instrument_refs": [editorial.LITERATURE[r] for r in (instrument or {}).get("refs", [])],
        "milestones": milestones,
        "chart": {
            "years": [y.year for y in years],
            "status": [y.status_in_year for y in years],
            "impl": [_r(y.implementation_level) for y in years],
            "capmf": [_r(y.capmf_stringency, 3) for y in years],
            "intensity": [_r(y.intensity_index) for y in years],
            "equal": [_r(y.intensity_index_equal) for y in years],
            "gated": [_r(y.intensity_index_equal_gated) for y in years],
            "src": [y.implementation_source for y in years],
            "detail": [y.implementation_detail for y in years],
            "temporal": [_r(y.temporal_weight) for y in years],
        },
    }


def emissions_context():
    """EPA 2023 sector emissions next to the number of policy series in each sector."""
    counts = defaultdict(int)
    for srs in m.PolicySeries.objects.all():
        counts[srs.sector] += 1
    rows = []
    for sector in glossary.SECTOR_ORDER:
        if sector not in editorial.SECTOR_EMISSIONS_2023:
            continue
        mt, note = editorial.SECTOR_EMISSIONS_2023[sector]
        share = None if sector == "LULUCF" else mt / editorial.EMISSIONS_TOTAL_2023
        rows.append({"sector": sector, "mt": mt, "share": share, "note": note, "series": counts.get(sector, 0),
                     "color": glossary.SECTORS[sector][0]})
    return rows
