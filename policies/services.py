"""Query helpers that turn database rows into compact JSON-ready structures."""
import re
from collections import Counter, defaultdict

from django.db.models import Prefetch

from . import editorial, glossary
from . import models as m
from .source_links import refresh_citation, resolve_url

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
    citations = [refresh_citation(c.strip()) for c in (series.source_citation or "").split("\n") if c.strip()]
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
        "notes": editorial.POLICY_NOTES.get(series.policy_id, []),
        # EEA-derived rows show the description Ireland reported; OECD-anchored
        # rows and residual bundles use the dashboard's own summaries.
        "eea_description": (series.layer != "residual" and bool(series.eea_pam_ids)
                            and series.policy_id not in glossary.POLICY_SUMMARIES),
        "reference_urls": [resolve_url(u) for u in re.findall(r"https?://[^\s;]+", series.reference_url or "")],
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


# ---------------------------------------------------------------- eligibility explanations
# Plain wording for the build notes recorded in the selection log's decision_basis field.
DECISION_NOTES = {
    "effect_assigned_once_to_primary_sector_for_selection":
        "Its reported saving is counted once, in its primary sector, when measures are ranked for selection.",
    "reported_zero_not_evidence_of_no_effect":
        "A reported saving of zero is not taken as evidence that the measure has no effect.",
    "source_date_conflict":
        "The source records give different dates for this measure; the start year used was reconciled "
        "(see the verification note on its policy profile).",
    "reported_deployment_portfolio_not_single_legal_instrument":
        "Reported as a deployment portfolio rather than a single legal instrument.",
    "LIEN_source_regulatory_label_reclassified_voluntary":
        "Reported to the EEA as “Regulatory”, but classified here as a voluntary agreement because membership is voluntary.",
    "expiry_of_reported_rebalancing_phase_not_abolition_of_taxes":
        "The end of the reported rebalancing phase is not treated as the abolition of the taxes.",
    "unallocated_multisector_effect_excluded_from_sector_ranking":
        "Its multi-sector saving cannot be allocated to one sector, so it is left out of the sector ranking.",
    "source_2020_start_reconciled_to_narrative_2022":
        "The EEA record gives a 2020 start; the record's own narrative dates implementation to 2022, which is used.",
    "liming_CO2_and_N2O_tradeoff":
        "Liming adds CO₂ but can reduce N₂O emissions; the trade-off is noted.",
    "negative_2030_projection_not_used_for_default_ranking":
        "Its negative 2030 projection is not used for the default ranking.",
}
EFFECT_SOURCES = {
    "expost_2024": "ex-post estimate for 2024 reported to the EEA",
    "exante_2025_WEM": "ex-ante projection for 2025, with existing measures, reported to the EEA",
}
ELIGIBILITY_TESTS = [
    ("A", "Mitigation purpose", "criteria_a_mitigation"),
    ("B", "Applies in Ireland", "criteria_b_ireland"),
    ("C", "Identifiable instrument or framework", "criteria_c_instrument"),
    ("D", "Identified start date", "criteria_d_start"),
    ("E", "Active within 2000–2023", "criteria_e_active"),
]


def _sentence(text):
    text = (text or "").strip()
    return text if not text or text.endswith((".", "!", "?")) else text + "."


def _clip(text, n=320):
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= n else text[:n].rsplit(" ", 1)[0] + " …"


def candidate_details():
    """Item-by-item reasoning for the five eligibility tests of every selection candidate.

    Built only from the stored release records (the selection log, Ireland's EEA records and the
    OECD CAPMF categories and scores). Returns {candidate_id: {"tests": [...], "notes": [...]}};
    each test is {"key", "label", "pass", "text", "evidence": [...]}.
    """
    pams = {p.pam_id: p for p in m.EeaPam.objects.all()}
    cats = {c.code: c for c in m.CapmfCategory.objects.all()}
    positive = defaultdict(list)
    for o in m.CapmfObservation.objects.filter(measure="POL_STRINGENCY", value__gt=0).order_by("year"):
        positive[o.category_id].append(o.year)
    names = dict(m.PolicySeries.objects.values_list("policy_id", "policy_name"))

    def policy_names(ids):
        out = []
        for i in (x.strip() for x in ids.split(";")):
            if not i:
                continue
            out.append(names.get(i) or (f"{i[4:]} residual bundle" if i.startswith("RES_") else i))
        return ", ".join(dict.fromkeys(out))

    result = {}
    for c in m.SelectionCandidate.objects.all():
        why, ev = {}, {k: [] for k, _, _ in ELIGIBILITY_TESTS}
        eea = c.candidate_origin.startswith("EEA")
        if eea:
            ids = [int(float(x)) for x in c.source_pam_ids.split(";") if x.strip()]
            recs = [pams[i] for i in ids if i in pams]
            # A measure can have one record per projection scenario; the dates come from the record(s) of
            # the measure as implemented, not from a planned-scenario variant
            recs = [r for r in recs if r.status != "Planned"] or recs
            rec = recs[0] if recs else None
            starts = sorted({r.start for r in recs if r.start})
            finishes = sorted({r.finish for r in recs if r.finish})
            statuses = sorted({r.status for r in recs if r.status})
            why["A"] = ("Reported by Ireland to the EEA as a climate policy or measure"
                        + (f" affecting {rec.ghgs}" if rec and rec.ghgs else "") + ".")
            if rec and rec.sectors:
                ev["A"].append(f"Sectors affected (EEA record): {rec.sectors}")
            if c.reported_effect_kt is not None:
                src = EFFECT_SOURCES.get(c.effect_source, c.effect_source.replace("_", " "))
                ev["A"].append(f"Reported saving: {c.reported_effect_kt:,.1f} kt CO₂-eq per year ({src})")
            elif c.effect_source == "not_quantified":
                ev["A"].append("The EEA record does not quantify an emission saving")
            why["B"] = "Part of Ireland's national report of policies and measures to the EEA."
            if ids:
                ev["B"].append(f"EEA policy-or-measure ID{'s' if len(ids) > 1 else ''}: {', '.join(map(str, ids))}"
                               + (" (one record per projection scenario)" if len(ids) > 1 else ""))
            why["C"] = (f"The EEA record names its instrument type: {rec.instrument_type}." if rec and rec.instrument_type
                        else "The EEA record describes the policy or measure.")
            if rec and rec.description:
                ev["C"].append(f"EEA description: “{_clip(rec.description)}”")
            if c.selected_start_year:
                why["D"] = f"Implementation start year used: {c.selected_start_year}."
                if starts and str(c.selected_start_year) not in starts:
                    ev["D"].append(f"The EEA record gives {', '.join(starts)}; {c.selected_start_year} is used after "
                                   "checking official sources (see the policy profile)")
                elif starts:
                    ev["D"].append(f"EEA implementation period start: {', '.join(starts)}")
            else:
                why["D"] = "No implementation start year is recorded."
            first = starts[0] if starts else (c.selected_start_year or "?")
            last = finishes[-1] if finishes else "no end date"
            why["E"] = f"EEA status: {', '.join(statuses) or 'not stated'}; implementation period {first} to {last}."
            if c.criteria_e_active:
                ev["E"].append("This period overlaps 2000–2023")
        else:
            cat = cats.get(c.candidate_id)
            yrs = positive.get(cat.id, []) if cat else []
            in_period = [y for y in yrs if 2000 <= y <= 2023]
            fpy = (cat.first_positive_year if cat else None) or (yrs[0] if yrs else None)
            why["A"] = ("An OECD CAPMF climate-mitigation policy category"
                        + (f" in the “{cat.domain}” module" if cat and cat.domain else "")
                        + f": {cat.label if cat else c.candidate_name}.")
            if cat and cat.instrument_class:
                ev["A"].append(f"OECD instrument class: {cat.instrument_class}")
            why["B"] = "The OECD scores this category for Ireland (country code IRL)."
            if fpy:
                ev["B"].append(f"First positive stringency score for Ireland: {fpy}")
            rep = cat.represented_by if cat else ""
            why["C"] = (f"Matched to named Irish instrument{'s' if ';' in rep else ''}: {policy_names(rep)}." if rep
                        else "The OECD category describes an identifiable type of instrument.")
            if c.decision_basis and not c.decision_basis.startswith("Conservative"):
                ev["C"].append(_sentence(c.decision_basis))
            why["D"] = (f"Start year used: {c.selected_start_year or fpy}." if c.criteria_d_start
                        else f"The OECD score is positive from {fpy}, but that is a scoring year, not the dated start of an identified instrument."
                        if fpy else "No start year can be identified.")
            why["E"] = (f"Positive OECD scores in {in_period[0]}–{in_period[-1]} ({len(in_period)} of the 24 years 2000–2023)."
                        if in_period else "No positive OECD score within 2000–2023.")

        passes = [getattr(c, f) for _, _, f in ELIGIBILITY_TESTS]
        first_fail = next((ELIGIBILITY_TESTS[i][0] for i, ok in enumerate(passes) if not ok), None)
        reason = _sentence(c.exclusion_reason)
        tests = []
        for (k, label, _), ok in zip(ELIGIBILITY_TESTS, passes):
            if ok:
                text = why.get(k, "")
            elif k == first_fail:
                text = reason or "Not established from the source records."
                if k in ("D", "E") and why.get(k):
                    text += " " + why[k]
            elif eea and reason:
                # the EEA exclusion reasons are specific to the measure and cover every test it fails
                text = reason + (" " + why[k] if k in ("D", "E") and why.get(k) else "")
            else:
                text = (f"Not met, because test {first_fail} failed: "
                        + ("a candidate without an established mitigation purpose is not dated or checked for activity."
                           if first_fail == "A" else
                           "without an identified instrument there is no instrument whose start or activity can be dated."
                           if first_fail == "C" else "see that test."))
                if k in ("D", "E") and why.get(k):
                    w = why[k]
                    text += " For reference: " + (w if w[1:2].isupper() else w[0].lower() + w[1:])
            tests.append({"key": k, "label": label, "pass": ok, "text": text, "evidence": ev[k]})

        notes = []
        for code in (x.strip() for x in c.decision_basis.split(";")):
            if code in DECISION_NOTES:
                notes.append(DECISION_NOTES[code])
            elif code.startswith("Conservative"):
                notes.append("Exclusion follows a conservative, evidence-based screen; it is not a claim that no such policy exists in Ireland.")
        if c.output_policy_ids:
            notes.append(("Retained as: " if c.outcome == "core" else "Grouped into: ") + policy_names(c.output_policy_ids) + ".")
        result[c.candidate_id] = {"tests": tests, "notes": notes}
    return result
