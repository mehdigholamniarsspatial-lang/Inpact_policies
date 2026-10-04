"""Plain-language vocabulary for every coded category in the dataset.

These explanations drive the tooltips, legends and category guide in the
dashboard, so readers never have to decode raw values such as
``L3_measure_programme`` or ``capmf_derived`` by themselves.
"""

SECTOR_ORDER = ["Cross-sectoral", "Electricity", "Buildings", "Industry", "Transport",
                "Agriculture", "LULUCF", "Waste", "F-gases"]

LAYER_ORDER = ["L1_framework", "L2_instrument", "L3_measure_programme", "residual"]

MECHANISM_ORDER = ["framework", "pricing", "standards", "obligations", "practice_regulation",
                   "deployment_support", "subsidies_finance", "information_voluntary", "mixed"]

SECTORS = {
    "Cross-sectoral": ("#46507A", "National climate laws and governance bodies that apply to the whole economy. Used only for L1 frameworks."),
    "Electricity": ("#C99A12", "Power generation: renewable supports, CHP and the EU ETS for power stations."),
    "Buildings": ("#B0503A", "Homes, public and commercial buildings: building regulations, retrofit grants, appliance rules and heating."),
    "Industry": ("#56636F", "Manufacturing and large energy users, including ETS installations, audits and energy networks."),
    "Transport": ("#2D78A8", "Road vehicles, fuels and aviation: carbon tax on motor fuels, biofuel obligation, car standards and EV supports."),
    "Agriculture": ("#5A9440", "Farm practices affecting methane and nitrous oxide, such as low-emission slurry spreading and liming."),
    "LULUCF": ("#2E6A50", "Land use, land-use change and forestry, e.g. peatland rehabilitation."),
    "Waste": ("#8A6A45", "Landfill and waste management, mainly methane from landfilled organic waste."),
    "F-gases": ("#7A5AA6", "Fluorinated gases used in refrigeration and vehicle air-conditioning."),
}

LAYERS = {
    "L1_framework": ("Framework", "L1", "Umbrella laws and governance: climate acts, carbon budgets, the advisory council. They set direction but do not cut emissions on their own, so they are never added to instruments."),
    "L2_instrument": ("Instrument", "L2", "A legal or economic lever that directly changes behaviour: a tax, a trading system, a building code or an obligation."),
    "L3_measure_programme": ("Programme", "L3", "A delivery scheme that implements policy on the ground, usually grants or support programmes run by agencies such as SEAI."),
    "residual": ("Residual bundle", "R", "One summary row per sector for the smaller eligible measures that were not selected individually. Its members are listed separately; do not count both."),
}

MECHANISMS = {
    "framework": ("#46507A", "Framework", "Sets targets, budgets and institutions rather than prices or rules for emitters."),
    "pricing": ("#0E7C74", "Pricing", "Puts a price on carbon, either through a tax (carbon tax, VRT) or a cap-and-trade system (EU ETS)."),
    "standards": ("#2F68A8", "Standards", "Mandatory minimum performance for products, vehicles or buildings, e.g. Part L building regulations or fleet-average CO\u2082 targets for new cars."),
    "obligations": ("#7B4F96", "Obligations", "Legal duties on companies to deliver an outcome, such as energy savings (EEOS) or biofuel blending."),
    "practice_regulation": ("#8B5A38", "Practice regulation", "Rules on how an activity is carried out, e.g. landfill limits, slurry spreading methods or new licence restrictions."),
    "deployment_support": ("#3D944B", "Deployment support", "Supports to build out clean supply, such as renewable electricity tariffs and auctions (REFIT/RESS)."),
    "subsidies_finance": ("#CC8A1E", "Subsidies & finance", "Grants, tax allowances and finance that lower the cost of cleaner investment."),
    "information_voluntary": ("#C0567A", "Information & voluntary", "Networks, advice and voluntary agreements that rely on engagement rather than enforcement."),
    "mixed": ("#8C969C", "Mixed (residual)", "Used only by residual bundles, which combine several mechanisms."),
}

STATUS = {
    "pre_implementation": ("Not yet started", "The year is before the policy's selected start year."),
    "active": ("Active", "The policy is in force in this year."),
    "post_expiry_residual": ("Expired, lingering effect", "The source phase ended, but documentation says effects continue; an assumed decay is applied."),
    "post_expiry_no_effect": ("Expired", "The policy ended and no continuing effect is assumed."),
}

IMPLEMENTATION_SOURCE = {
    "capmf_derived": ("OECD score", "Implementation comes from the matched OECD CAPMF stringency score in the same year, divided by 10."),
    "assumed": ("Assumed timing", "No matching OECD score was usable, so a hypothetical ramp-up profile is used (or a structural zero before the start)."),
}

MATCH_CONFIDENCE = {
    "exact": ("Exact", "The OECD category measures this same instrument."),
    "close": ("Close", "The OECD category measures the instrument family this policy belongs to."),
    "partial": ("Partial", "The OECD category is only contextual, e.g. a general financing or governance indicator."),
    "none": ("No match", "No OECD category covers this policy; it comes from the EEA registry only."),
}

SELECTION_RULE = {
    "materiality_90pct": ("Top-impact", "Selected because, ranked by reported savings, it is among the measures that together reach 90% of its sector's reported total."),
    "anchor_capmf": ("OECD anchor", "Selected because it is a named instrument represented in the OECD CAPMF with positive stringency."),
    "residual": ("Residual", "Eligible, but grouped into its sector's residual bundle."),
}

SOURCE_DATASETS = {
    "EEA": ("EEA only", "Found only in the EEA policies-and-measures registry that Ireland reports to the EU."),
    "CAPMF": ("OECD only", "Added from the OECD CAPMF as a named anchor; no EEA record."),
    "EEA+CAPMF": ("Both", "An EEA registry record linked to an OECD CAPMF category."),
}

AGGREGATION_ROLE = {
    "policy_or_programme": "Stand-alone policy row.",
    "family_representative_no_child_duplicate": "Represents a consolidated family (e.g. successive Part L vintages); its components are not repeated.",
    "framework_context_never_aggregate": "Framework context only; never add it to instrument rows.",
    "portfolio_context_choose_parent_or_delivery_schemes": "A portfolio. Use either this parent or its delivery schemes, not both.",
    "residual_summary_do_not_also_include_members": "Residual summary. Do not also include its member measures.",
}

METRICS = {
    "intensity_index": ("Policy intensity", "0\u20131", "Implementation \u00d7 coverage \u00d7 bindingness. The dataset's main composite: how strongly a policy bears on its sector in a year. A relative index, not tonnes."),
    "implementation_level": ("Implementation level", "0\u20131", "Implementation proxy: the OECD stringency score / 10 when matched (policy design stringency, not observed compliance), otherwise an assumed ramp-up."),
    "capmf_stringency": ("OECD stringency", "0\u201310", "The raw OECD CAPMF stringency score for the matched category. Blank where there is no usable match."),
    "intensity_index_equal_gated": ("Equal-weight intensity", "0\u20131", "Simple average of implementation, coverage and bindingness, set to zero before the policy starts. A sensitivity check on the main index."),
}

COVERAGE_SCORES = {1.0: "Whole sector or economy", 0.5: "Major subsector or broad programme",
                   0.25: "Defined technology, cohort or segment", 0.1: "Narrow pilot or niche"}
BINDINGNESS_SCORES = {1.0: "Mandatory rule or statutory framework", 0.75: "Price or statutory obligation",
                      0.5: "Financial incentive", 0.25: "Information or voluntary"}

FLAG_GROUPS = {
    "Scoring conventions": ["normative_bindingness", "ordinal_coverage", "literal_equal_mean_positive_when_inactive"],
    "Timing assumptions": ["assumed_timing", "assumed_post_expiry_decay", "open_end_snapshot_reconstruction",
                           "capmf_first_positive_start_not_verified_enactment", "capmf_first_positive_start"],
    "OECD match quality": ["CAPMF_category_proxy_not_programme_specific", "CAPMF_missing_not_backcast",
                           "CAPMF_zero_while_recorded_active", "industrial_category_proxy",
                           "implementation_source_switch_not_policy_change", "shared_governance_indicator"],
    "Source conflicts": ["source_date_conflict", "source_start_conflict_pam53", "source_expiry_conflict_pam12",
                         "CAPMF_nonres_first_positive_2008_vs_EEA_2005", "source_2020_start_reconciled_to_narrative_2022"],
    "Aggregation warnings": ["framework_context_not_additive", "not_separate_causal_effect", "family_consolidation",
                             "residual_strict_mean_of_fixed_members", "residual_product_of_means_not_used",
                             "mixed_mechanisms_residual_exception", "family_effect_sum_for_selection_bookkeeping_only",
                             "reported_deployment_portfolio_not_single_legal_instrument"],
    "Selection context": ["retrospective_selection", "effect_assigned_once_to_primary_sector_for_selection",
                          "unallocated_multisector_effect_excluded_from_sector_ranking",
                          "reported_zero_not_evidence_of_no_effect", "negative_2030_projection_not_used_for_default_ranking"],
}


def humanise(code: str) -> str:
    """Turn an underscore code into readable sentence-case text."""
    if not code:
        return ""
    text = code.replace("_", " ").strip()
    return text[:1].upper() + text[1:]


def flag_group(flag: str) -> str:
    for group, flags in FLAG_GROUPS.items():
        if flag in flags:
            return group
    return "Policy-specific notes"


def as_payload():
    """Everything the front end needs to label and colour categories."""
    return {
        "sectors": {k: {"color": c, "desc": d} for k, (c, d) in SECTORS.items()},
        "sectorOrder": SECTOR_ORDER,
        "layers": {k: {"label": l, "short": s, "desc": d} for k, (l, s, d) in LAYERS.items()},
        "layerOrder": LAYER_ORDER,
        "mechanisms": {k: {"color": c, "label": l, "desc": d} for k, (c, l, d) in MECHANISMS.items()},
        "mechanismOrder": MECHANISM_ORDER,
        "status": {k: {"label": l, "desc": d} for k, (l, d) in STATUS.items()},
        "implSource": {k: {"label": l, "desc": d} for k, (l, d) in IMPLEMENTATION_SOURCE.items()},
        "match": {k: {"label": l, "desc": d} for k, (l, d) in MATCH_CONFIDENCE.items()},
        "selection": {k: {"label": l, "desc": d} for k, (l, d) in SELECTION_RULE.items()},
        "sources": {k: {"label": l, "desc": d} for k, (l, d) in SOURCE_DATASETS.items()},
        "metrics": {k: {"label": l, "unit": u, "desc": d} for k, (l, u, d) in METRICS.items()},
    }


# Short plain-language summaries for policies added from the OECD CAPMF, which
# have no EEA registry description. EEA-derived policies use the official text.
POLICY_SUMMARIES = {
    "CAPMF_ACT_2015": "Ireland's first climate law. It required national mitigation and adaptation plans, annual transition statements to the Oireachtas, and established the Climate Change Advisory Council.",
    "CAPMF_ACT_2021": "Amended the 2015 Act to put Ireland on a legally binding path to climate neutrality by 2050 and a 51% cut by 2030 (from 2018). It introduced five-year carbon budgets, sectoral emissions ceilings and annual Climate Action Plans.",
    "CAPMF_CARBON_BUDGETS": "Five-year national limits on total greenhouse-gas emissions. The first carbon-budget programme, comprising budgets for 2021\u201325 and 2026\u201330 and a provisional budget for 2031\u201335, was approved in 2022; the dataset starts it in 2022, when the programme took effect on 6 April.",
    "CAPMF_SECTOR_CEILINGS": "Divides the carbon budgets into maximum emissions for each sector of the economy, such as electricity, transport, buildings, industry and agriculture. Agreed by Government in July 2022.",
    "CAPMF_NET_ZERO": "The statutory national objective, set in the 2021 Act, to achieve a climate-neutral economy no later than 2050.",
    "CAPMF_CLIMATE_COUNCIL": "Independent statutory body that advises Government on climate policy, proposes carbon budgets and reviews progress each year.",
    "CAPMF_EU_ETS": "The EU's cap-and-trade system. Power stations and large industrial sites must surrender an allowance for each tonne of CO\u2082 they emit; aviation was brought in from 2012.",
    "CAPMF_PARTL_RES": "Part L of the Building Regulations sets energy-performance requirements for new homes and major renovations. Successive editions tightened the standard, up to Nearly Zero Energy Building (NZEB) levels.",
    "CAPMF_PARTL_NONRES": "Part L of the Building Regulations for offices, shops, schools and other non-residential buildings. Successive editions tightened the standard, up to NZEB levels.",
    "CAPMF_EE_AUDITS": "Large enterprises must carry out an energy audit at least every four years, under the EU Energy Efficiency Directive as transposed by S.I. 426/2014.",
    "CAPMF_MEPS_MOTOR": "EU ecodesign regulations set minimum efficiency classes for electric motors, which drive much of industrial electricity use.",
    "CAPMF_MEPS_APPL": "EU ecodesign rules set minimum energy performance for appliances such as fridges, freezers, lighting and air conditioners, taking the least efficient products off the market.",
    "CAPMF_LABEL_APPL": "The EU energy label must be displayed on appliances such as fridges, freezers, lamps and air conditioners, so buyers can compare efficiency.",
    "CAPMF_LABEL_CAR": "New passenger cars must display fuel-consumption and CO\u2082 information at the point of sale (EU Car Labelling Directive 1999/94/EC).",
    "CAPMF_FOSSIL_LICENCES": "The 2021 Climate Act restricted the granting of new petroleum authorisations for oil and gas exploration and extraction. Existing authorisations were preserved, and their holders may seek successor authorisations under the statutory saving provisions.",
}
