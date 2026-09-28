"""Load the Ireland core climate-policy release into the Django database.

Usage:
    python manage.py load_policy_data              # uses settings.POLICY_DATA_DIR
    python manage.py load_policy_data --data-dir /path/to/ireland_core_policy_release

The command is idempotent: every table is cleared and rebuilt. It accepts
either this project's trimmed ``data/`` folder or the original release folder
(it looks for raw inputs in both ``raw/`` and ``inputs/raw/``).
"""
from pathlib import Path

import numpy as np
import pandas as pd
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from policies import models as m
from policies.editorial import (COLUMN_RENAMES, DICTIONARY, METHOD_DECISIONS, REFERENCE_TITLES, VALIDATION,
                                clean_reference_date, clean_text, format_citations)
from policies.glossary import SECTOR_ORDER, LAYER_ORDER, POLICY_SUMMARIES


def clean(value, default=""):
    """Convert pandas missing values to a model-friendly default."""
    if value is None:
        return default
    if isinstance(value, float) and np.isnan(value):
        return default
    if value is pd.NA or value is pd.NaT:
        return default
    return value


def num(value):
    value = clean(value, None)
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def integer(value):
    value = num(value)
    return None if value is None else int(round(value))


def first_existing(root: Path, *candidates):
    for c in candidates:
        p = root / c
        if p.exists():
            return p
    return None


class Command(BaseCommand):
    help = "Import the Ireland core policy timeline release into the database."

    def add_arguments(self, parser):
        parser.add_argument("--data-dir", default=None, help="Folder containing the release files")

    def handle(self, *args, **opts):
        root = Path(opts["data_dir"] or settings.POLICY_DATA_DIR).resolve()
        main_csv = root / "ireland_core_policy_timeline.csv"
        if not main_csv.exists():
            raise CommandError(f"Cannot find {main_csv}. Point --data-dir at the release folder.")
        self.root = root
        with transaction.atomic():
            self.clear()
            self.load_series(main_csv)
            self.load_selection()
            self.load_residual_members()
            self.load_small_tables()
            self.load_capmf()
            self.load_eea()
        self.stdout.write(self.style.SUCCESS(
            f"Loaded {m.PolicySeries.objects.count()} policy-sector series, "
            f"{m.PolicyYear.objects.count()} annual rows, "
            f"{m.SelectionCandidate.objects.count()} candidates, "
            f"{m.CapmfCategory.objects.count()} CAPMF categories, "
            f"{m.EeaPam.objects.count()} EEA records."
        ))

    # ------------------------------------------------------------------
    def clear(self):
        for model in [m.PolicyYear, m.PolicySeries, m.SelectionCandidate, m.ResidualMember,
                      m.OverlapRelation, m.SectorMateriality, m.Reference, m.ValidationCheck,
                      m.ReconciliationEntry, m.DictionaryField, m.CapmfObservation,
                      m.CapmfCategory, m.EeaPam]:
            model.objects.all().delete()

    def read(self, *names):
        path = first_existing(self.root, *names)
        if path is None:
            return None
        return pd.read_csv(path)

    # ------------------------------------------------------------------
    def load_series(self, main_csv):
        df = pd.read_csv(main_csv)
        classification = self.read("config/pam_classification.csv")
        anchors = self.read("config/anchor_register.csv")

        desc_lookup, url_lookup = {}, {}
        if classification is not None:
            for _, r in classification.iterrows():
                key = (r["policy_id"], r["sector"])
                if clean(r.get("source_description")):
                    desc_lookup.setdefault(key, r["source_description"])
                    desc_lookup.setdefault((r["policy_id"], None), r["source_description"])
                if clean(r.get("source_reference")):
                    url_lookup.setdefault(r["policy_id"], r["source_reference"])
        anchor_basis = {}
        if anchors is not None:
            for _, r in anchors.iterrows():
                anchor_basis[(r["policy_id"], r["sector"])] = clean(r.get("start_year_basis"))

        sector_rank = {s: i for i, s in enumerate(SECTOR_ORDER)}
        layer_rank = {s: i for i, s in enumerate(LAYER_ORDER)}

        groups = df.groupby(["policy_id", "sector"], sort=False)
        year_rows = []
        for (pid, sector), g in groups:
            g = g.sort_values("year")
            r = g.iloc[0]
            flags = sorted({f for v in g["data_quality_flag"].dropna() for f in str(v).split(";") if f})
            description = (POLICY_SUMMARIES.get(pid) or desc_lookup.get((pid, sector))
                           or desc_lookup.get((pid, None)) or "")
            if not description and r["layer"] == "residual":
                n = int(r["eligible_member_count"])
                noun = "measure" if n == 1 else "measures"
                description = (f"Summary row for {n} other eligible {sector} {noun} that did not enter "
                               f"the core set individually. Its intensity is the average of the members' "
                               f"own intensity values; the members are listed below.")
            if not description:
                basis = anchor_basis.get((pid, sector)) or clean(r["start_year_basis"])
                description = f"{clean(r['coverage_rationale'])} Start-date basis: {basis}".strip()
            last = g[g["year"] == g["year"].max()].iloc[0]
            series = m.PolicySeries.objects.create(
                slug=f"{pid}--{sector}".lower().replace(" ", "-").replace("_", "-"),
                policy_id=pid,
                policy_name=r["policy_name"],
                sector=sector,
                layer=r["layer"],
                bundle=r["bundle"],
                mechanism=r["mechanism"],
                mechanism_class=clean(r["mechanism_class"]),
                regime=clean(r["regime"]),
                instrument_type=clean(r["instrument_type"]),
                ghg_affected=clean(r["ghg_affected"]),
                source_datasets=clean(r["source_datasets"]),
                eea_pam_ids=str(clean(r["eea_pam_ids"])),
                all_eea_variant_ids=str(clean(r["all_eea_variant_ids"])),
                prior_policy_ids=str(clean(r["prior_policy_ids"])),
                capmf_code=clean(r["capmf_code"]),
                match_confidence=clean(r["match_confidence"]),
                capmf_match_scope=clean(r["capmf_match_scope"]),
                selection_rule=clean(r["selection_rule"]),
                materiality_group_flag=bool(r["materiality_group_flag"]),
                anchor_flag=bool(r["anchor_flag"]),
                multi_sector_flag=bool(r["multi_sector_flag"]),
                sector_effect_rank=num(r["sector_effect_rank"]),
                reported_effect_kt=num(r["reported_effect_kt"]),
                effect_source=clean(r["effect_source"]),
                effect_reference_year=integer(r["effect_reference_year"]),
                effect_value_state=clean(r["effect_value_state"]),
                materiality_sector=clean(r["materiality_sector"]),
                start_year=int(r["start_year"]),
                end_year=integer(r["end_year"]),
                start_year_basis=clean_text(clean(r["start_year_basis"])),
                legacy=clean(r["legacy"]),
                coverage_share=num(r["coverage_share"]),
                coverage_rationale=clean_text(clean(r["coverage_rationale"])),
                bindingness=num(r["bindingness"]),
                bindingness_rationale=clean_text(clean(r["bindingness_rationale"])),
                source_citation="\n".join(format_citations(clean(r["source_citation"]))),
                aggregation_role=clean(r["aggregation_role"]),
                member_policy_ids=str(clean(r["member_policy_ids"])),
                score_family_id=clean(r["score_family_id"]),
                lag_years=num(r["lag_years"]),
                ramp_years=num(r["ramp_years"]),
                half_life_years=num(r["half_life_years"]),
                parameter_basis=clean_text(clean(r["parameter_basis"])),
                eligible_member_count=int(r["eligible_member_count"]),
                data_quality_flags=";".join(flags),
                description=clean_text(description),
                reference_url=clean(url_lookup.get(pid, ""))[:500],
                peak_intensity=num(g["intensity_index"].max()),
                intensity_2023=num(last["intensity_index"]),
                capmf_years=int((g["implementation_source"] == "capmf_derived").sum()),
                assumed_years=int(((g["implementation_source"] == "assumed") & (g["status_in_year"] != "pre_implementation")).sum()),
                sort_order=sector_rank.get(sector, 99) * 1000 + layer_rank.get(r["layer"], 9) * 100
                + max(0, min(99, int(r["start_year"]) - 1950)),
            )
            for _, y in g.iterrows():
                year_rows.append(m.PolicyYear(
                    series=series,
                    year=int(y["year"]),
                    status_in_year=y["status_in_year"],
                    years_since_start=int(y["years_since_start"]),
                    implementation_source=clean(y["implementation_source"]),
                    implementation_level=num(y["implementation_level"]),
                    capmf_stringency=num(y["capmf_stringency"]),
                    intensity_index=num(y["intensity_index"]),
                    intensity_index_equal=num(y["intensity_index_equal"]),
                    intensity_index_equal_gated=num(y["intensity_index_equal_gated"]),
                    temporal_weight=num(y["temporal_weight"]),
                    implementation_detail=clean_text(clean(y["implementation_detail"])),
                    capmf_observation_status=str(clean(y["capmf_observation_status"])),
                    data_quality_flag=clean(y["data_quality_flag"]),
                ))
        m.PolicyYear.objects.bulk_create(year_rows, batch_size=500)

    # ------------------------------------------------------------------
    def load_selection(self):
        s = self.read("selection_log.csv")
        objs = []
        for _, r in s.iterrows():
            eligible = bool(r["eligible"])
            rule = clean(r["selection_rule"])
            outcome = "excluded" if not eligible else ("residual" if rule == "residual" else "core")
            objs.append(m.SelectionCandidate(
                candidate_id=r["candidate_id"],
                candidate_origin=r["candidate_origin"],
                candidate_name=r["candidate_name"],
                source_pam_ids=str(clean(r["source_pam_ids"])),
                eligible=eligible,
                criteria_a_mitigation=bool(r["eligibility_a_mitigation"]),
                criteria_b_ireland=bool(r["eligibility_b_Ireland"]),
                criteria_c_instrument=bool(r["eligibility_c_instrument_or_framework"]),
                criteria_d_start=bool(r["eligibility_d_identified_start"]),
                criteria_e_active=bool(r["eligibility_e_active_2000_2023"]),
                exclusion_reason=clean_text(clean(r["exclusion_reason"])),
                selection_rule=rule,
                materiality_group_flag=bool(clean(r["materiality_group_flag"], False)),
                anchor_flag=bool(clean(r["anchor_flag"], False)),
                primary_sector=clean(r["primary_sector"]),
                reported_effect_kt=num(r["reported_effect_kt"]),
                effect_source=clean(r["effect_source"]),
                sector_effect_rank=num(r["sector_effect_rank"]),
                cumulative_effect_share=num(r["cumulative_effect_share"]),
                selected_start_year=integer(r["selected_start_year"]),
                reported_end_year=integer(r["reported_end_year"]),
                output_policy_ids=str(clean(r["output_policy_ids"])),
                decision_basis=clean(r["decision_basis"]),
                outcome=outcome,
            ))
        m.SelectionCandidate.objects.bulk_create(objs)

    def load_residual_members(self):
        r = self.read("qa/residual_members.csv")
        if r is None:
            return
        objs = []
        for (pid, sector), g in r.groupby(["policy_id", "sector"], sort=False):
            first = g.iloc[0]
            last = g.sort_values("year").iloc[-1]
            objs.append(m.ResidualMember(
                residual_sector=sector, policy_id=pid, policy_name=first["policy_name"],
                mechanism=clean(first["mechanism"]), layer=clean(first["layer"]),
                start_year=integer(first["start_year"]), end_year=integer(first["end_year"]),
                reported_effect_kt=num(first["reported_effect_kt"]),
                coverage_share=num(first["coverage_share"]), bindingness=num(first["bindingness"]),
                intensity_2023=num(last["intensity_index"]),
            ))
        m.ResidualMember.objects.bulk_create(objs)

    def load_small_tables(self):
        o = self.read("overlap_register.csv")
        m.OverlapRelation.objects.bulk_create([
            m.OverlapRelation(parent_id=r["parent_or_related_id"], related_id=r["related_policy_id"],
                              relationship=r["relationship"], treatment=r["treatment"])
            for _, r in o.iterrows()])
        s = self.read("sector_materiality.csv")
        m.SectorMateriality.objects.bulk_create([
            m.SectorMateriality(
                sector=r["sector"], eligible_pam_units=int(r["eligible_pam_units"]),
                positive_quantified_units=int(r["positive_quantified_units"]),
                materiality_units=int(r["materiality_units"]),
                ranking_total_kt=num(r["ranking_total_kt"]), selected_ranking_kt=num(r["selected_ranking_kt"]),
                achieved_share=num(r["achieved_share"]), assessment=clean(r["assessment"]),
                interpretation=clean(r["interpretation"]))
            for _, r in s.iterrows()])
        ref = self.read("config/references.csv", "references.csv")
        refs = []
        for _, r in ref.iterrows():
            pub, title, date = REFERENCE_TITLES.get(r["source_id"], (clean(r["publisher"]), clean(r["title"]),
                                                                     clean_reference_date(r["publication_date"])))
            refs.append(m.Reference(source_id=r["source_id"], publisher=pub, title=title, publication_date=date,
                                    url=clean(r["url"])[:600], locator="", access_status=""))
        m.Reference.objects.bulk_create(refs)
        v = self.read("validation_report.csv")
        m.ValidationCheck.objects.bulk_create([
            m.ValidationCheck(check_name=r["check"], result=r["result"],
                              detail=VALIDATION.get(r["check"], (None, clean_text(r["detail"])))[1])
            for _, r in v.iterrows()])
        m.ReconciliationEntry.objects.bulk_create([
            m.ReconciliationEntry(topic=topic, issue="", decision=text, locator="") for topic, text in METHOD_DECISIONS])
        d = self.read("data_dictionary.csv")
        m.DictionaryField.objects.bulk_create([
            m.DictionaryField(position=int(r["position"]), column=COLUMN_RENAMES.get(r["column"], r["column"]),
                              unit=clean(r["unit"]).replace("Excel row identifiers", "record positions"),
                              definition=DICTIONARY.get(COLUMN_RENAMES.get(r["column"], r["column"]),
                                                        clean_text(r["definition_and_derivation"])))
            for _, r in d.iterrows()])

    # ------------------------------------------------------------------
    def load_capmf(self):
        path = first_existing(self.root, "raw/capmf_ireland.csv", "inputs/raw/Ireland  OECD CAPMF (3).csv")
        if path is None:
            self.stdout.write(self.style.WARNING("CAPMF raw CSV not found; skipping CAPMF explorer data."))
            return
        raw = pd.read_csv(path)
        meta = self.read("reference/capmf_categories.csv", "inputs/prior_chatgpt/capmf_categories.csv")
        elig = self.read("config/capmf_eligibility.csv")
        meta_map = {} if meta is None else meta.set_index("capmf_code").to_dict("index")
        elig_map = {} if elig is None else elig.set_index("candidate_id").to_dict("index")

        labels = raw.drop_duplicates("CLIM_ACT_POL").set_index("CLIM_ACT_POL")["Climate actions and policies"]
        cats = {}
        for code, label in labels.items():
            level = int(code.split("_")[0].replace("LEV", ""))
            mm = meta_map.get(code, {})
            ee = elig_map.get(code, {})
            cats[code] = m.CapmfCategory.objects.create(
                code=code, label=label, level=level,
                domain=clean(mm.get("domain")), instrument_class=clean(mm.get("instrument_class")),
                first_positive_year=integer(ee.get("first_positive_year")),
                eligible=None if not ee else bool(ee.get("eligible")),
                exclusion_reason=clean_text(clean(ee.get("exclusion_reason"))),
                represented_by=clean(ee.get("represented_by")),
            )
        obs = []
        for _, r in raw.iterrows():
            status = clean(r["OBS_STATUS"], "A")
            value = num(r["OBS_VALUE"])
            if status in ("M", "K"):
                value = None
            obs.append(m.CapmfObservation(category=cats[r["CLIM_ACT_POL"]], measure=r["MEASURE"],
                                          year=int(r["TIME_PERIOD"]), value=value, status=status))
        m.CapmfObservation.objects.bulk_create(obs, batch_size=1000)

    def load_eea(self):
        path = first_existing(self.root, "raw/eea_pams_ireland.xlsx", "inputs/raw/Ireland Pams(3).xlsx")
        if path is None:
            self.stdout.write(self.style.WARNING("EEA workbook not found; skipping EEA record details."))
            return
        e = pd.read_excel(path)
        lineage = self.read("policy_id_lineage.csv")
        lin = {} if lineage is None else dict(zip(lineage["pam_id"], lineage["policy_id"]))
        objs = []
        for _, r in e.iterrows():
            pid = int(r["ID of policy or measure"])
            objs.append(m.EeaPam(
                pam_id=pid, policy_id=clean(lin.get(pid, "")),
                name=clean(r["Name of policy or measure"]),
                scenario=clean(r["Projection scenario in which the policy or measure is included"]),
                status=clean(r["Status of implementation"]),
                start=str(integer(r["Implementation period start"]) or ""),
                finish=str(integer(r["Implementation period finish"]) or ""),
                instrument_type=clean(r["Type of policy instrument"]),
                sectors=clean(r["Sectors  affected"]),
                ghgs=clean(r["GHGs  affected"]),
                description=clean(r["Description"]),
                expost_kt=num(r["Average expost emission reduction  kt CO2eq y GHG"]),
                wem_2030_kt=num(r["Total GHG emissions reductions in 2030  kt CO2eq y GHG"]),
            ))
        m.EeaPam.objects.bulk_create(objs)
