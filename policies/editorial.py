"""Editorial content for the public dashboard.

This module holds all curated, publication-grade text: instrument explanations,
policy milestones, emissions context, the data dictionary, validation-check
descriptions and methodological decisions. It also provides the text cleaner
that converts internal build notes in the source tables (file names, row
numbers, retrieval-status codes, drafting labels) into neutral scientific
wording before anything is shown or exported.
"""
import re

# ---------------------------------------------------------------------------
# Literature and official sources cited across the dashboard
# ---------------------------------------------------------------------------
LITERATURE = {
    "NACHTIGALL2022": "Nachtigall, D., Lutz, L., Cárdenas Rodríguez, M., Haščič, I. and Pizarro, R. (2022). The climate actions and policies measurement framework: A structured and harmonised climate policy database to monitor countries' mitigation action. OECD Environment Working Papers, No. 203. OECD Publishing, Paris.",
    "KRUSE2022": "Kruse, T., Dechezleprêtre, A., Saffar, R. and Robert, L. (2022). Measuring environmental policy stringency in OECD countries: An update of the OECD composite EPS indicator. OECD Economics Department Working Papers, No. 1703. OECD Publishing, Paris.",
    "STECHEMESSER2024": "Stechemesser, A., Koch, N., Mark, E., Dilger, E., Klösel, P., Menicacci, L., Nachtigall, D., Pretis, F., Ritter, N., Schwarz, M., Vossen, H. and Wenzel, A. (2024). Climate policies that achieved major emission reductions: Global evidence from two decades. Science, 385(6711), 884–892.",
    "GOVREG": "Regulation (EU) 2018/1999 of the European Parliament and of the Council on the Governance of the Energy Union and Climate Action (Article 18: reporting on policies and measures and projections).",
    "IMPLREG": "Commission Implementing Regulation (EU) 2020/1208 on the structure, format, submission processes and review of information reported by Member States pursuant to Regulation (EU) 2018/1999.",
    "OECDJRC2008": "OECD and European Commission Joint Research Centre (2008). Handbook on Constructing Composite Indicators: Methodology and User Guide. OECD Publishing, Paris.",
    "IPCC2022": "IPCC (2022). Climate Change 2022: Mitigation of Climate Change. Contribution of Working Group III to the Sixth Assessment Report, Chapter 13: National and Sub-national Policies and Institutions. Cambridge University Press.",
    "EPA2026": "Environmental Protection Agency (2026). Ireland's Final Greenhouse Gas Emissions 1990–2024. EPA, Wexford.",
    "BAUMOL1971": "Baumol, W.J. and Oates, W.E. (1971). The use of standards and prices for protection of the environment. Swedish Journal of Economics, 73(1), 42–54.",
    "GOULDER2008": "Goulder, L.H. and Parry, I.W.H. (2008). Instrument choice in environmental policy. Review of Environmental Economics and Policy, 2(2), 152–174.",
    "JAFFE1994": "Jaffe, A.B. and Stavins, R.N. (1994). The energy-efficiency gap: What does it mean? Energy Policy, 22(10), 804–810.",
    "ALLCOTT2012": "Allcott, H. and Greenstone, M. (2012). Is there an energy efficiency gap? Journal of Economic Perspectives, 26(1), 3–28.",
    "MARTIN2016": "Martin, R., Muûls, M. and Wagner, U.J. (2016). The impact of the European Union Emissions Trading Scheme on regulated firms: What is the evidence after ten years? Review of Environmental Economics and Policy, 10(1), 129–148.",
    "COUTURE2010": "Couture, T. and Gagnon, Y. (2010). An analysis of feed-in tariff remuneration models: Implications for renewable energy investment. Energy Policy, 38(2), 955–965.",
    "ROSENOW2017": "Rosenow, J. and Bayer, E. (2017). Costs and benefits of Energy Efficiency Obligations: A review of European programmes. Energy Policy, 107, 53–62.",
    "FANKHAUSER2018": "Fankhauser, S., Averchenkova, A. and Finnegan, J. (2018). 10 years of the UK Climate Change Act. Grantham Research Institute on Climate Change and the Environment, London School of Economics.",
}

# ---------------------------------------------------------------------------
# Policy-instrument guide (one entry per mechanism used in the dataset)
# ---------------------------------------------------------------------------
INSTRUMENTS = {
    "framework": {
        "title": "Framework legislation and climate governance",
        "definition": "Statutes and institutions that set long-term mitigation objectives, binding emission budgets, planning and reporting cycles, and independent scrutiny. They do not themselves prescribe what emitters must do.",
        "rationale": "Climate policy requires commitments that outlast electoral cycles. Framework laws address this time-inconsistency problem by making targets statutory, creating recurring planning obligations and assigning accountability. Independent advisory bodies reduce information asymmetries between government and parliament.",
        "ireland": "The Climate Action and Low Carbon Development Act 2015 introduced national mitigation and adaptation plans and established the Climate Change Advisory Council. The Amendment Act 2021 made climate neutrality by 2050 a legal objective and set a 51% cut in emissions by 2030, compared with 2018. It also introduced five-year carbon budgets, sectoral emissions ceilings and annual Climate Action Plans.",
        "strengths": ["Raises the credibility and predictability of long-term policy", "Coordinates action across sectors and departments", "Creates regular accountability through reporting and review"],
        "limitations": ["Acts indirectly, through the instruments it mandates", "Effects are difficult to attribute separately from those instruments", "Targets can be missed without automatic corrective measures"],
        "measurement": "Framework rows form layer L1 and are assigned to the cross-sectoral category. Implementation is proxied by OECD governance indicators (climate advisory body, net-zero target status). Several frameworks share the same indicator, so they are contextual and must never be added to instrument rows.",
        "refs": ["FANKHAUSER2018", "IPCC2022", "NACHTIGALL2022"],
    },
    "pricing": {
        "title": "Carbon pricing: taxes and emissions trading",
        "definition": "Instruments that attach an explicit price to greenhouse-gas emissions. A carbon tax fixes the price and lets the quantity adjust; an emissions trading system fixes the quantity (the cap) and lets the price adjust. Emissions-based vehicle taxation applies the same logic to purchase and ownership taxes.",
        "rationale": "Emissions impose an external cost that market prices do not reflect. A single carbon price corrects this. Each emitter cuts emissions wherever doing so costs less than the price. So the overall cut is achieved at the lowest total cost. It also rewards continuing innovation.",
        "ireland": "Ireland's carbon tax applies to fossil fuels outside the EU Emissions Trading System (ETS). It began on motor fuels in December 2009, at €15 per tonne of CO₂. Non-transport fuels followed at the same rate in May 2010. The rate rose to €20 in 2012 and, after a long plateau, to €26 in 2020. The Finance Act 2020 legislated annual increases of €7.50 towards €100 per tonne by 2030. Power stations and large industrial installations have been covered by the EU Emissions Trading System since 2005, and aviation since 2012. Vehicle registration tax and motor tax were rebased on CO₂ emissions in 2008.",
        "strengths": ["Cost-effective allocation of abatement across emitters", "Continuous incentive to innovate", "Generates revenue that can offset distributional effects"],
        "limitations": ["Historical price levels were low relative to estimated social costs", "Exemptions and free allocation weaken the signal", "Short-run demand for fuels is price-inelastic", "Regressive effects unless revenue is recycled"],
        "measurement": "Implementation uses OECD price indicators (carbon-tax rate by sector, ETS price, aviation pricing). Pricing rows are split into those inside the EU ETS and those outside it (covered by the EU Effort Sharing Regulation, ESR). Bindingness is scored 0.75 (price or statutory obligation).",
        "refs": ["BAUMOL1971", "GOULDER2008", "MARTIN2016", "KRUSE2022"],
    },
    "standards": {
        "title": "Performance standards and mandatory labelling",
        "definition": "Mandatory minimum energy or emissions performance for buildings, appliances, motors and vehicles, together with compulsory disclosure of that performance through labels.",
        "rationale": "Energy use in durable goods responds weakly to prices because of imperfect information, limited attention and split incentives, for example between landlords and tenants. This is the so-called energy-efficiency gap. Standards remove the least efficient options from the market. Labels reduce search costs for buyers.",
        "ireland": "Part L of the Building Regulations has been tightened repeatedly for dwellings and other buildings, culminating in Nearly Zero Energy Building (NZEB) requirements. EU ecodesign and energy-labelling rules apply to appliances, lighting and electric motors. New cars must meet EU fleet CO₂ standards, first under Regulation (EC) 443/2009 and then Regulation (EU) 2019/631. They must also carry a CO₂ label at the point of sale.",
        "strengths": ["Predictable performance outcomes", "Effective where price responsiveness is weak", "Drive technology diffusion across the EU single market"],
        "limitations": ["Apply mainly to new stock, so effects accrue slowly with turnover", "Gaps between test-cycle and real-world performance", "Rebound effects", "Generally less cost-effective than an equivalent price signal"],
        "measurement": "Implementation uses OECD indicators for building energy codes, minimum energy-performance standards and labels. Successive editions of each standard are grouped into one policy family. Bindingness is scored 1.0 (enforced rule). Assumed timing profiles use long ramps reflecting stock turnover.",
        "refs": ["JAFFE1994", "ALLCOTT2012", "GOULDER2008"],
    },
    "obligations": {
        "title": "Market-based obligations",
        "definition": "Legal duties on specified market actors, such as energy suppliers, fuel suppliers or large enterprises, to deliver a quantified outcome. Firms usually have flexibility in how they comply.",
        "rationale": "Obligations combine a regulatory target with market flexibility. The obligated party finds the least-cost way to meet it, which is useful where many small, dispersed actions are needed, for example household energy savings.",
        "ireland": "The Energy Efficiency Obligation Scheme (2014), under Article 7 of the EU Energy Efficiency Directive, requires energy suppliers to deliver verified end-use savings. Biofuel support began with excise relief in the mid-2000s; the Biofuels Obligation Scheme took effect in 2010. Large enterprises must carry out energy audits every four years under S.I. 426/2014.",
        "strengths": ["Quantified, verifiable targets", "Flexible and often low-cost delivery", "Does not require public expenditure"],
        "limitations": ["Additionality of reported savings can be uncertain", "Compliance costs are passed through to consumers", "For biofuels, life-cycle and land-use emissions may offset gains"],
        "measurement": "Most obligation rows are unmatched in the OECD framework and use assumed timing; audits use the OECD energy-efficiency mandate indicator. Bindingness is scored 0.75 for statutory obligations and 1.0 where the duty is directly enforced.",
        "refs": ["ROSENOW2017", "IPCC2022"],
    },
    "practice_regulation": {
        "title": "Regulation of practices and activities",
        "definition": "Rules governing how an emitting activity is carried out, or restricting it outright. Examples include landfill limits, prescribed agricultural techniques and restrictions on new fossil-fuel licensing.",
        "rationale": "Some emissions come from many scattered farm or waste processes, or from long-lived investments. Here, setting rules on practices can be easier to monitor and enforce than pricing each tonne.",
        "ireland": "The EU Landfill Directive (1999/31/EC) set targets for diverting biodegradable waste from landfill, reinforced nationally by a landfill levy introduced in 2002. Low-emission slurry spreading (trailing shoe, trailing hose or injection) reduces ammonia losses and associated nitrous oxide. The Climate Action and Low Carbon Development (Amendment) Act 2021 ended new licences for oil and gas exploration and extraction.",
        "strengths": ["Directly targets the emitting process", "Relatively easy to verify compliance", "Addresses non-CO₂ gases that are hard to price"],
        "limitations": ["Limited flexibility in how abatement is achieved", "Enforcement over many small actors is resource-intensive", "Supply-side restrictions may shift rather than reduce emissions"],
        "measurement": "Agriculture and waste practices have no direct OECD stringency indicator, so implementation uses assumed timing. Licensing restrictions use the OECD fossil-fuel extraction ban indicator. Bindingness is scored 1.0 (enforced rule).",
        "refs": ["IPCC2022", "GOULDER2008"],
    },
    "deployment_support": {
        "title": "Deployment support for renewable energy",
        "definition": "Revenue or price support that guarantees returns to renewable generators and heat producers. Examples include feed-in tariffs, auctioned contracts for difference and renewable-heat supports.",
        "rationale": "Early deployment lowers future costs through learning-by-doing, a benefit that investors cannot fully capture. Long-term revenue certainty also lowers the cost of capital for projects with high upfront costs.",
        "ireland": "Renewable electricity was first supported by the Alternative Energy Requirement competitions. The REFIT feed-in tariff schemes followed from 2006. Since 2020, support comes through competitive auctions under the Renewable Electricity Support Scheme (RESS). Renewables supplied 40.7% of electricity in 2023. Renewable heat is supported through the Support Scheme for Renewable Heat and related measures.",
        "strengths": ["Rapid scale-up of clean supply", "Lower financing costs through revenue certainty", "Auctions reveal costs and drive prices down"],
        "limitations": ["Costs recovered from consumers through levies", "Poorly designed tariffs can over-compensate", "Grid and planning constraints limit delivery"],
        "measurement": "The renewable-electricity portfolio uses the average of the OECD feed-in-tariff and auction scores as context. The two programmes can coexist, so neither is assumed to replace the other. Renewable heat has no OECD indicator and uses assumed timing. Bindingness is scored 0.5 (financial incentive).",
        "refs": ["COUTURE2010", "IPCC2022"],
    },
    "subsidies_finance": {
        "title": "Subsidies, tax allowances and finance",
        "definition": "Grants, accelerated capital allowances and concessional finance that reduce the upfront cost of low-carbon investment by households, firms and communities.",
        "rationale": "High upfront costs, credit constraints and high implicit discount rates deter investments that pay back over time. Subsidies also support markets and supply chains for new technologies.",
        "ireland": "SEAI delivers most programmes. They include home retrofit grants (Better Energy Homes) and free upgrades for households at risk of energy poverty (Warmer Homes). Others support community and business retrofits and, from 2011, electric vehicles. There is also the Accelerated Capital Allowance, a tax relief. The allowance lets companies deduct 100% of the cost of qualifying energy-efficient equipment in the year of purchase. In agriculture, liming supports improve soil conditions.",
        "strengths": ["Directly addresses capital barriers", "Politically acceptable and visible", "Can be targeted at low-income households"],
        "limitations": ["Free-riding: some supported investments would have happened anyway", "Uptake often skews to higher-income groups", "Fiscal cost per tonne can be high"],
        "measurement": "OECD financing indicators give only general context for specific programmes (a partial match). Most programme rows therefore rely on assumed timing. Bindingness is scored 0.5 (financial incentive).",
        "refs": ["ALLCOTT2012", "JAFFE1994", "IPCC2022"],
    },
    "information_voluntary": {
        "title": "Information, networks and voluntary agreements",
        "definition": "Advice, energy-management networks, benchmarking and voluntary commitments that rely on engagement rather than legal compulsion.",
        "rationale": "Organisations often lack the information, skills or management attention to identify cost-effective savings. Peer networks and structured energy management address these organisational failures at low public cost.",
        "ireland": "The Large Industry Energy Network (LIEN), run by SEAI, supports companies with high energy spend in energy management and annual reporting. The Public Sector Programme supports public bodies in meeting energy-efficiency targets, including a 33% improvement target for 2020.",
        "strengths": ["Low cost", "Builds capability that supports other instruments", "Encourages disclosure and benchmarking"],
        "limitations": ["Participants self-select, so savings may not be additional", "No enforcement if commitments are missed"],
        "measurement": "No OECD indicator applies, so implementation uses assumed timing. Bindingness is scored 0.25 (information or voluntary).",
        "refs": ["ALLCOTT2012", "IPCC2022"],
    },
    "mixed": {
        "title": "Residual bundles (mixed mechanisms)",
        "definition": "One summary row per sector for eligible measures that were not selected individually, combining several mechanisms.",
        "rationale": "Retaining smaller measures as a residual keeps every eligible policy represented without inflating the core set.",
        "ireland": "Residual bundles cover smaller retrofit, heat, microgeneration, agriculture and peatland measures.",
        "strengths": ["Complete coverage of eligible measures", "Transparent member lists"],
        "limitations": ["Heterogeneous content", "The bundle's mean is not comparable with a single instrument"],
        "measurement": "Intensity is the mean of the members' intensities. If any member is missing, the bundle value is missing too. Members must not be counted in addition to the bundle.",
        "refs": ["OECDJRC2008"],
    },
}

# ---------------------------------------------------------------------------
# Verified contextual milestones for major policies (not used in the index)
# ---------------------------------------------------------------------------
POLICY_MILESTONES = {
    "IRL_P0005": [
        (2009, "Carbon tax applied to petrol and diesel at €15 per tonne CO₂ (December)."),
        (2010, "Extended to other liquid and gaseous fuels (non-transport fuels) at €15 per tonne (1 May)."),
        (2012, "Rate raised to €20 per tonne."),
        (2013, "Solid fuels (non-transport fuels) brought within the carbon tax, phased in at a lower initial rate."),
        (2020, "Rate raised to €26 per tonne; the Finance Act 2020 legislated annual rises of €7.50 towards €100 per tonne by 2030."),
        (2021, "€33.50 per tonne on non-transport fuels (1 May)."),
        (2022, "€41.00 per tonne on non-transport fuels (1 May)."),
        (2023, "€48.50 per tonne on non-transport fuels (1 May)."),
    ],
    "CAPMF_EU_ETS": [
        (2005, "Phase 1 (2005–2007): power stations and large industrial installations covered."),
        (2008, "Phase 2 (2008–2012) begins, aligned with the Kyoto commitment period."),
        (2012, "Aviation brought into the system."),
        (2013, "Phase 3 (2013–2020): single EU-wide cap; auctioning becomes the default for power generation."),
        (2019, "Market Stability Reserve starts to absorb surplus allowances."),
        (2021, "Phase 4 (2021–2030) begins with a faster annual reduction in the cap."),
    ],
    "IRL_P0019": [(2008, "Vehicle registration tax and annual motor tax for new cars rebased on CO₂ emission bands (July).")],
    "IRL_P0020": [
        (2009, "Regulation (EC) 443/2009 adopted, with a 130 g CO₂/km fleet-average target phased in from 2012 to 2015."),
        (2020, "Regulation (EU) 2019/631 applies, continuing and tightening fleet CO₂ standards for cars and vans."),
    ],
    "CAPMF_PARTL_RES": [
        (2019, "Part L revision introduces Nearly Zero Energy Building (NZEB) performance for new dwellings."),
    ],
    "CAPMF_PARTL_NONRES": [
        (2017, "S.I. 538/2017 amends Part L to introduce NZEB requirements for new buildings other than dwellings, applying from 2019."),
    ],
    "IRL_P0026": [
        (2006, "REFIT feed-in tariff introduced for renewable electricity."),
        (2020, "First auction under the Renewable Electricity Support Scheme (RESS 1)."),
        (2023, "Renewables supply 40.7% of electricity (EPA)."),
    ],
    "IRL_P0027": [(2010, "Biofuels Obligation Scheme takes effect, requiring fuel suppliers to include a share of biofuels.")],
    "IRL_P0032": [(2014, "Energy Efficiency Obligation Scheme established under Article 7 of the Energy Efficiency Directive (2012/27/EU).")],
    "CAPMF_EE_AUDITS": [(2014, "S.I. 426/2014 requires large enterprises to carry out energy audits at least every four years; first deadline December 2015.")],
    "IRL_P0024": [
        (1999, "EU Landfill Directive 1999/31/EC sets targets for diverting biodegradable municipal waste from landfill."),
        (2002, "National landfill levy introduced, later increased in stages."),
    ],
    "IRL_P0023": [
        (2011, "Mobile Air Conditioning Directive 2006/40/EC bans refrigerants with a global warming potential above 150 in new vehicle types."),
        (2017, "The ban extends to all newly registered cars."),
    ],
    "CAPMF_MEPS_MOTOR": [(2011, "Ecodesign Regulation (EC) 640/2009 sets minimum IE2 efficiency for new electric motors, tightened in later stages.")],
    "CAPMF_ACT_2015": [(2015, "Climate Action and Low Carbon Development Act enacted (10 December).")],
    "CAPMF_CLIMATE_COUNCIL": [(2016, "Climate Change Advisory Council established on a statutory basis (18 January).")],
    "CAPMF_ACT_2021": [(2021, "Climate Action and Low Carbon Development (Amendment) Act enacted (23 July).")],
    "CAPMF_CARBON_BUDGETS": [(2022, "First two carbon budgets (2021–2025 and 2026–2030) approved and take effect (6 April).")],
    "CAPMF_SECTOR_CEILINGS": [(2022, "Government agrees sectoral emissions ceilings for the first two budget periods (28 July).")],
}

# ---------------------------------------------------------------------------
# Emissions context: EPA final inventory, 2023 values (Mt CO2eq)
# ---------------------------------------------------------------------------
EMISSIONS_SOURCE = ("Environmental Protection Agency, final greenhouse-gas inventory 1990–2024 (March 2026), "
                    "values for 2023. Dashboard sectors aggregate EPA categories as noted.")
EMISSIONS_TOTAL_2023 = 54.934
SECTOR_EMISSIONS_2023 = {
    "Agriculture": (20.717, "Agriculture"),
    "Transport": (11.798, "Transport"),
    "Electricity": (7.860, "Energy Industries (mainly power generation, also refining)"),
    "Buildings": (6.733, "Residential 5.347 + Commercial services 0.715 + Public services 0.671"),
    "Industry": (6.307, "Manufacturing combustion 4.152 + Industrial processes 2.155"),
    "Waste": (0.844, "Waste"),
    "F-gases": (0.675, "F-gases"),
    "LULUCF": (3.895, "Net source from land use, land-use change and forestry (excluded from the national total)"),
}

# ---------------------------------------------------------------------------
# Readable explanations for data-quality flags
# ---------------------------------------------------------------------------
FLAG_TEXT = {
    "normative_bindingness": "Bindingness is a normative score from the study rubric, not a measure of observed compliance.",
    "ordinal_coverage": "Coverage is an ordinal scope score, not a measured share of activity or emissions.",
    "retrospective_selection": "Policies were selected using recent (2024–2030) assessments, which can introduce retrospective selection bias.",
    "open_end_snapshot_reconstruction": "The policy has no reported end date; its status after the reporting date is reconstructed as continuing.",
    "literal_equal_mean_positive_when_inactive": "The unweighted equal-weight index remains positive before the policy starts; use the gated version for timing analysis.",
    "effect_assigned_once_to_primary_sector_for_selection": "A multi-sector reported saving was assigned once, to the primary sector, for ranking only.",
    "assumed_timing": "Implementation in some years follows an assumed ramp-up because no matching OECD score is available.",
    "CAPMF_category_proxy_not_programme_specific": "The matched OECD indicator describes the broader category, not this specific programme.",
    "framework_context_not_additive": "Framework row: contextual, and never added to instrument rows.",
    "not_separate_causal_effect": "Should not be interpreted as a separate causal effect.",
    "shared_governance_indicator": "Shares an OECD governance indicator with other framework rows.",
    "mixed_mechanisms_residual_exception": "The residual bundle combines several mechanisms.",
    "residual_product_of_means_not_used": "The bundle's intensity is not the product of its mean components.",
    "residual_strict_mean_of_fixed_members": "The bundle's intensity is the mean over a fixed member list; any missing member makes it missing.",
    "reported_deployment_portfolio_not_single_legal_instrument": "The row represents a portfolio of support schemes rather than a single legal instrument.",
    "capmf_first_positive_start_not_verified_enactment": "The start year is the first year with a positive OECD score, not a verified enactment date.",
    "source_date_conflict": "Sources disagree on a date; the conflict is documented and the selected date is justified.",
    "unallocated_multisector_effect_excluded_from_sector_ranking": "An unallocated multi-sector saving was excluded from sector ranking.",
    "family_consolidation": "Several source records (for example successive regulatory editions) are consolidated into one family.",
    "reported_zero_not_evidence_of_no_effect": "A reported saving of zero is retained as reported and is not evidence of no effect.",
    "CAPMF_missing_not_backcast": "Missing OECD values are left missing and never filled from other years.",
    "assumed_post_expiry_decay": "After expiry, a lingering effect is modelled with an assumed half-life.",
    "family_effect_sum_for_selection_bookkeeping_only": "The family's summed reported saving is used for selection bookkeeping only.",
    "vintage_changes_not_measured": "Changes in stringency between regulatory editions are not separately measured.",
    "label_not_energy_performance": "A labelling requirement signals information, not a performance level.",
    "heterogeneous_products": "Covers heterogeneous product groups.",
    "CAPMF_nonres_first_positive_2008_vs_EEA_2005": "The EEA reports implementation from 2005, while the OECD indicator first becomes positive in 2008.",
    "source_start_conflict_pam53": "A source record gives a different start year; the difference is documented.",
    "source_expiry_conflict_pam12": "A source record reports an expiry that conflicts with the continuing family; the difference is documented.",
    "ETS_exemptions_changed_2019": "ETS exemption rules changed in 2019.",
    "first_compliance_2015": "The first compliance deadline fell in 2015.",
    "industrial_category_proxy": "Uses an industry-wide OECD category as a proxy.",
    "new_licences_not_all_production": "Applies to new licences, not to all existing production.",
    "upstream_extraction_in_Industry_not_manufacturing": "Upstream extraction is placed in the industry sector, although it is not manufacturing.",
    "capmf_first_positive_start": "The start year follows the first positive OECD score.",
    "electricity_indirect_effect": "Effects on electricity emissions are indirect.",
    "expiry_of_reported_rebalancing_phase_not_abolition_of_taxes": "The reported end marks the close of a rebalancing phase, not abolition of the taxes.",
    "aviation_inventory_boundary": "ETS aviation scope differs from domestic aviation in the national inventory.",
    "label_not_fleet_standard": "A consumer label, not a binding fleet standard.",
    "family_extended_beyond_expired_pam20": "The family continues beyond an expired source record because a successor regulation applies.",
    "regulation_not_observed_fleet_uptake": "Measures the regulation, not observed fleet uptake.",
    "liming_CO2_and_N2O_tradeoff": "Liming releases CO₂ while potentially reducing N₂O; the net effect is uncertain.",
    "negative_2030_projection_not_used_for_default_ranking": "A negative 2030 projection was not used for default ranking.",
    "LIEN_source_regulatory_label_reclassified_voluntary": "Reclassified from 'regulatory' in the source to 'voluntary agreement', reflecting its design.",
    "source_2020_start_reconciled_to_narrative_2022": "A 2020 start in one field was reconciled to 2022 based on the source description.",
    "CAPMF_zero_while_recorded_active": "The OECD score is zero in some years in which the policy is recorded as active.",
    "implementation_source_switch_not_policy_change": "The implementation source switches between assumed and OECD-derived; this is not a policy change.",
}

# ---------------------------------------------------------------------------
# Data dictionary (publication version)
# ---------------------------------------------------------------------------
COLUMN_RENAMES = {"prior_policy_ids": "legacy_policy_ids", "claude_policy_unit_ids": "analytical_unit_ids"}

DICTIONARY = {
    "year": "Calendar year; complete annual grid 2000–2023.",
    "period_type": "Always 'historical': a retrospective reconstruction, not information available to decision-makers at the time.",
    "policy_id": "Canonical identifier of the policy family (IRL_ for EEA-derived policies, CAPMF_ for OECD-anchored instruments, RES_ for residual bundles).",
    "policy_name": "Standardised policy or instrument-family name; residual rows are sector summaries.",
    "layer": "Hierarchical level: L1 framework, L2 instrument, L3 delivery programme, or residual. Layers must not be summed.",
    "bundle": "Sector and mechanism grouping; pricing bundles distinguish ETS and non-ETS (ESR) regimes.",
    "sector": "Affected sector (Electricity, Buildings, Industry, Transport, Agriculture, LULUCF, Waste, F-gases), or Cross-sectoral for national frameworks.",
    "multi_sector_flag": "1 if the policy appears in more than one sector. Repeated rows do not imply that effects are allocated between sectors.",
    "regime": "Emissions regime affected: EU ETS, non-ETS (ESR), LULUCF, or mixed. ESR is a harmonised label for non-ETS scope across the whole period.",
    "mechanism": "Policy mechanism (see the instrument guide). Residual bundles are 'mixed'.",
    "instrument_type": "Instrument type as reported in the EEA database, with documented corrections where the label contradicts the policy design.",
    "ghg_affected": "Greenhouse gases affected (CO₂, CH₄, N₂O, F-gases, or all).",
    "source_datasets": "Source lineage: EEA, CAPMF, or both.",
    "eea_pam_ids": "Identifiers of historical EEA policy-and-measure records contributing to the row.",
    "capmf_code": "Matched OECD CAPMF indicator code(s), preferring level 4; parent and child levels are never mixed within one score.",
    "match_confidence": "Judgement of the OECD match: exact (same instrument), close (instrument family), partial (contextual proxy) or none.",
    "selection_rule": "Reason for inclusion: 90% materiality rule, OECD anchor, or residual.",
    "sector_effect_rank": "Rank of the reported saving within the primary selection sector (descending).",
    "reported_effect_kt": "Reported annual saving (kt CO₂e) used for selection only. Repeated across years and sectors; must never be summed or treated as an observed effect.",
    "effect_source": "Assessment from which the reported saving is taken: ex-post (2024), ex-ante with existing measures (2025) or ex-ante (2030).",
    "start_year": "Selected start year. Where based on the first positive OECD score, this is distinguished from a verified legal date.",
    "end_year": "Reported end of the source phase (inclusive); blank if open or continuing.",
    "status_in_year": "Status in the year: not yet started, active, expired with lingering effect, or expired with no effect.",
    "years_since_start": "Year minus start year; negative before the start.",
    "implementation_raw_value": "Reserved for independently observed implementation data (rates, uptake, expenditure). Blank in this version: no such series is available.",
    "implementation_raw_unit": "Unit of the observed implementation value; blank in this version.",
    "implementation_source": "Source of the implementation level: OECD-derived or assumed (including structural zeros before the start).",
    "implementation_level": "Implementation on a 0–1 scale: same-year OECD stringency ÷ 10 where matched; otherwise an assumed timing profile. After expiry, an assumed half-life decay may apply.",
    "capmf_stringency": "Same-year OECD CAPMF stringency (0–10); mean of distinct matched codes where several apply. Flags M and K are treated as missing; no values are imputed.",
    "coverage_share": "Ordinal scope score (0.1, 0.25, 0.5, 1). Despite the name, it is not a measured share of activity or emissions.",
    "coverage_rationale": "Justification for the scope score.",
    "bindingness": "Ordinal bindingness score: 1 enforced rule or statutory framework, 0.75 price or statutory obligation, 0.5 financial incentive, 0.25 information or voluntary.",
    "intensity_index": "Policy intensity = implementation × coverage × bindingness (0–1). For residuals, the strict mean of member intensities. A relative indicator, not a causal effect.",
    "intensity_index_equal": "Unweighted mean of implementation, coverage and bindingness; positive even before a policy starts.",
    "data_quality_flag": "Semicolon-separated quality flags (source conflicts, proxy scope, ordinal judgements, assumed timing, consolidation, residual rules).",
    "source_citation": "Official sources supporting the row.",
    "mechanism_class": "Timing class used for assumed implementation profiles (for example stock of buildings, price flow, asset subsidy).",
    "all_eea_variant_ids": "All EEA record variants linked to the policy, including planned-measure scenarios kept for provenance only.",
    "legacy_policy_ids": "Identifiers of source policy identities consolidated into the canonical row.",
    "analytical_unit_ids": "Identifiers of intermediate analytical units linked through the original EEA records.",
    "capmf_match_scope": "Scope of the OECD match: instrument family, category context or framework context.",
    "materiality_group_flag": "1 if at least one source member passed the sector 90% materiality rule.",
    "anchor_flag": "1 if retained under the OECD anchor rule.",
    "effect_reference_year": "Reference year of the reported saving (2024, 2025 or 2030).",
    "effect_value_state": "State of the reported saving: positive, negative, zero, missing, family sum or mixed.",
    "effect_source_field": "EEA reporting field used for the reported saving.",
    "materiality_sector": "Primary sector to which a multi-sector saving is assigned once for ranking.",
    "materiality_effect_kt": "Saving used for ranking in the primary sector only; not a measured sector allocation.",
    "start_year_basis": "Evidence and reasoning behind the start year.",
    "legacy": "Whether effects are reported to continue after expiry.",
    "bindingness_rationale": "Justification for the bindingness score.",
    "source_row_numbers": "Record positions in the source EEA extract, for traceability.",
    "aggregation_role": "How the row may be combined with others (framework context, family representative, portfolio, residual summary, stand-alone).",
    "member_policy_ids": "Policy identities represented by the row; for residuals, the fixed member list.",
    "implementation_detail": "Detailed source of the implementation value (OECD-derived, timing fallback, structural zero, assumed decay, residual averaging).",
    "capmf_observation_status": "OECD observation flags: A normal, E estimated, K included elsewhere, M not applicable.",
    "temporal_weight": "Assumed timing profile (0–1) evaluated for every row, even where OECD data determine implementation. Not an empirical response curve.",
    "lag_years": "Assumed lag before implementation begins (years).",
    "ramp_years": "Assumed duration of the linear phase-in (years).",
    "half_life_years": "Assumed half-life of lingering effects after expiry (years), applied only where sources indicate continuing effects.",
    "parameter_basis": "Status of the timing parameters: scenario assumptions, not empirically estimated.",
    "intensity_index_equal_gated": "Equal-weight index set to zero before the start and after an explicit end of effect; a sensitivity check on the main index.",
    "coverage_score_type": "Confirms that coverage is an ordinal scope score, not a measured share.",
    "effect_scope": "Warning that reported savings repeat across years and sectors and must not be summed.",
    "score_family_id": "OECD code set (or policy ID if unmatched). Rows sharing a code set share contextual information.",
    "eligible_member_count": "For residuals, the fixed number of analytical members.",
    "valid_intensity_member_count": "Number of members with a non-missing intensity value.",
}

# ---------------------------------------------------------------------------
# Validation checks (publication wording)
# ---------------------------------------------------------------------------
VALIDATION = {
    "01_unique_policy_sector_year": ("Unique keys", "Exactly one row per policy (or residual), sector and year."),
    "02_no_WAM_or_group_policy": ("Historical records only", "Planned-measure scenarios and group summary records are never treated as historical policies; they are kept only as provenance."),
    "03_required_labels_complete": ("Complete classification", "Every row has all classification and source labels."),
    "04_normalized_bounds": ("Valid ranges", "All normalised values lie in [0, 1]; missing values occur only where documented by a flag."),
    "05_raw_observation_citations": ("No fabricated observations", "No independent observed implementation series is available, so those fields are intentionally blank."),
    "06_framework_separation": ("Frameworks kept separate", "National framework rows are never placed in an instrument or programme bundle."),
    "07_ETS_scope": ("ETS scope", "All three EU ETS sector slices are labelled with the ETS regime."),
    "08_materiality_90pct_quantifiable_sectors": ("90% materiality rule", "Every sector with a positive reported total reaches the 90% threshold. Sectors with a zero total (LULUCF) are reported as not assessable, not as 100%."),
    "09_complete_year_grid": ("Complete time series", "Every policy–sector series has 24 annual rows."),
    "10_no_inventory_or_observed_emissions_used": ("No outcome data in construction", "No emissions inventory or observed emissions enter the construction; reported savings are used only for selection."),
    "11_product_formula": ("Intensity formula", "Intensity equals implementation × coverage × bindingness for every policy row. Residual rows use the mean of member intensities."),
    "12_zero_primary_intensity_before_start": ("Zero before start", "The main intensity index is zero before each policy starts; the unweighted equal-weight index is retained separately with a gated companion."),
    "13_residual_strict_means": ("Strict residual means", "Residual means use a fixed denominator and never silently drop missing members."),
    "14_CAPMF_no_imputation": ("No imputation of OECD data", "OECD values are used only for the same year; there is no back-casting or carrying forward."),
    "15_all_candidates_logged": ("All candidates documented", "All 68 EEA policy identities and 47 positive OECD categories are documented with a decision."),
    "16_every_eligible_PaM_represented": ("Every eligible policy represented", "Each eligible EEA policy appears either in a core family or in a residual bundle."),
    "17_no_duplicated_child_after_family_merge": ("No double counting", "Records consolidated into a family (Part L editions, appliance standards) do not appear again as separate rows."),
    "18_no_effect_value_in_intensity": ("Savings excluded from intensity", "Reported savings never enter the intensity calculation."),
    "19_source_identity_reconciliation": ("Traceable identities", "Every original EEA record is linked to its canonical policy."),
    "20_zero_negative_preservation": ("Zero and negative estimates kept", "Reported zero and negative estimates are retained as reported, without truncation."),
}

# ---------------------------------------------------------------------------
# Key methodological decisions (publication wording)
# ---------------------------------------------------------------------------
METHOD_DECISIONS = [
    ("Policy identities", "Ireland's EEA submission has 104 records: 98 individual measures and 6 group records that only summarise other records, so the groups are set aside. The 98 individual EEA records are consolidated into 68 policy identities by merging scenario variants (existing and additional measures). All original identifiers remain linked to the canonical policies."),
    ("Time window", "The analysis window is 2000–2023 (OECD scores are available for 1990–2023). Policies that started before 2000 keep their original start years. Planned measures are never activated and OECD scores are not extended beyond 2023."),
    ("OECD data", "OECD stringency scores are used only for the year in which they are observed. Where no score is available, a clearly labelled assumed timing profile is used instead; the two sources are never mixed silently."),
    ("Reported savings", "Reported emission savings determine which policies are selected but never enter the intensity index. No emissions inventory is used in the construction."),
    ("Zero and negative estimates", "The first available numeric estimate is retained even if it is zero or negative. Such values are reported as they are, not treated as missing."),
    ("Group and planned records", "Group summary records and planned measures are not treated as historical policies, and their effects are not divided among members."),
    ("Instrument matching", "OECD indicators are matched only where they describe the same instrument or its family. For example, the Energy Efficiency Obligation Scheme on suppliers is kept separate from mandatory audits for large enterprises. Likewise, boiler rules are not matched to the whole building code."),
    ("Renewable electricity", "Feed-in tariffs and auctions can coexist. The portfolio therefore uses the mean of both OECD indicators, and planning measures are not treated as funding."),
    ("Building regulations", "Successive Part L editions are consolidated into two families, dwellings and other buildings, so that the same OECD score is not counted repeatedly."),
    ("National anchors", "Some major instruments are missing from the EEA registry. To include them, the dataset adds six national framework records, the EU ETS in each sector and other verified regulations."),
    ("Timing parameters", "Lag, ramp-up and half-life values are scenario assumptions, not estimates from the literature. After expiry, any lingering effect starts from the last operational level."),
    ("Coverage", "Coverage is scored on an ordinal legal-scope scale. It is explicitly not a physical share of activity or emissions."),
    ("Equal-weight index", "The unweighted mean of the three components is provided unchanged, together with a gated version that is zero before a policy starts."),
    ("Retrospective selection", "Policies were selected using recent (2024–2030) assessments, which may bias the results, especially in causal analysis. Test such analyses with alternative selections."),
]

# ---------------------------------------------------------------------------
# Text cleaning
# ---------------------------------------------------------------------------
_MECH_LABELS = {
    "framework": "framework", "pricing": "pricing", "standards": "standards", "obligations": "obligation",
    "practice_regulation": "practice-regulation", "deployment_support": "deployment-support",
    "subsidies_finance": "subsidy and finance", "information_voluntary": "information and voluntary", "mixed": "mixed",
}

_REPLACEMENTS = [
    (re.compile(r"Prompt normative rubric;?\s*"), "Assigned from the study's normative bindingness rubric; "),
    (re.compile(r"Prompt rubric applied to (\w+);?\s*"),
     lambda m: f"Assigned from the study's bindingness rubric for {_MECH_LABELS.get(m.group(1), m.group(1).replace('_', ' '))} instruments; "),
    (re.compile(r"Claude supplied judgement scenario; not empirically fitted or independently literature-validated"),
     "Scenario assumption specified by the study; not empirically estimated or independently validated"),
    (re.compile(r"Conventional legal-presence fallback only; no empirical governance-response interpretation"),
     "Conventional legal-presence profile; no empirical governance response is implied"),
    (re.compile(r";?\s*see residual_members\.csv for individual dates"), "; member start dates are listed individually"),
    (re.compile(r"See fixed member mechanisms in residual_members\.csv"), "Member-specific timing parameters apply"),
    (re.compile(r"First supplied EEA"), "First reported EEA"),
    (re.compile(r"source dates retained in selection log"), "source dates documented in the selection record"),
    (re.compile(r"not resolved in this release"), "not resolved in this version"),
    (re.compile(r"\bsupplied/imported\b"), "available"),
    (re.compile(r"Claude_midyear_timing_fallback"), "midyear_timing_fallback"),
    (re.compile(r"\s{2,}"), " "),
]


def clean_text(value):
    """Rewrite internal build wording into neutral publication wording."""
    if not value or not isinstance(value, str):
        return value
    text = value
    for pattern, repl in _REPLACEMENTS:
        text = pattern.sub(repl, text)
    return text.strip().rstrip(";").strip()


def _fmt_date(iso):
    months = ["January", "February", "March", "April", "May", "June", "July", "August",
              "September", "October", "November", "December"]
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", iso)
    if not m:
        return iso
    return f"{int(m.group(3))} {months[int(m.group(2)) - 1]} {m.group(1)}"


def _clean_citation(seg):
    seg = seg.strip().rstrip(";").strip()
    m = re.match(r"EEA\. Ireland PaMs report (\d+), PaM (\d+)", seg)
    if m:
        return (f"European Environment Agency. Reporting on national policies and measures, Ireland "
                f"(report {m.group(1)}), PaM {m.group(2)}. https://pam.apps.eea.europa.eu/")
    m = re.match(r"EEA report (\d+) PaMs ([\d;]+)", seg)
    if m:
        ids = ", ".join(m.group(2).strip(";").split(";"))
        noun = "PaM" if "," not in ids else "PaMs"
        return (f"European Environment Agency. Reporting on national policies and measures, Ireland "
                f"(report {m.group(1)}), {noun} {ids}. https://pam.apps.eea.europa.eu/")
    if seg.startswith("OECD. CAPMF Ireland export"):
        url = re.search(r"https://\S+", seg)
        return ("OECD. Climate Actions and Policies Measurement Framework (CAPMF) database, Ireland, 1990–2023. "
                + (url.group(0) + " " if url else "") + "(accessed 25 September 2026)")
    seg = re.sub(r"\(accessed (\d{4}-\d{2}-\d{2});[^)]*\)", lambda mm: f"(accessed {_fmt_date(mm.group(1))})", seg)
    return seg


def format_citations(raw):
    """Split a raw citation field into a list of clean, deduplicated references."""
    if not raw:
        return []
    parts = []
    for block in str(raw).split(" | "):
        # some fields join several references with ';' directly after a closing bracket or full stop
        for seg in re.split(r"(?<=[).]);(?=[A-Z])", block):
            if seg.strip():
                parts.append(_clean_citation(seg))
    seen, out = set(), []
    for p in parts:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


REFERENCE_TITLES = {
    "CAPMF_EXPORT": ("OECD", "Climate Actions and Policies Measurement Framework (CAPMF) database, Ireland, 1990–2023", "2025"),
    "OECD_TECH": ("OECD", "CAPMF database documentation", "2022"),
    "EEA_APP": ("European Environment Agency", "Integrated national climate and energy policies and measures database", "2026"),
}


def clean_reference_date(value):
    v = str(value or "")
    if v.startswith("accessed"):
        return "n.d."
    m = re.search(r"(\d{4})", v)
    return m.group(1) if m else v

# Comparative overview of mechanisms (Instruments page)
COMPARISON = {
    "framework": ("Targets, budgets and institutions", "Government, through subsequent plans", "1.0", "Climate advisory body; net-zero target"),
    "pricing": ("Price per tonne of emissions", "Each emitter", "0.75", "Carbon tax rates; ETS price and coverage; aviation pricing"),
    "standards": ("Minimum performance of products, vehicles, buildings", "Regulator sets the level; producers choose how", "1.0", "Building codes; MEPS; energy labels; vehicle CO₂ standards"),
    "obligations": ("Quantified duty on market actors", "Obligated firms", "0.75 or 1.0", "Energy-efficiency mandates"),
    "practice_regulation": ("Prescribed or restricted practices", "Regulator", "1.0", "Fossil-fuel extraction bans"),
    "deployment_support": ("Guaranteed revenue for clean supply", "Investors, within scheme rules", "0.5", "Feed-in tariffs; renewable auctions"),
    "subsidies_finance": ("Lower cost of low-carbon investment", "Households and firms (voluntary uptake)", "0.5", "Financing mechanisms for energy efficiency"),
    "information_voluntary": ("Knowledge, networks, commitments", "Participants", "0.25", "None in the CAPMF"),
}
