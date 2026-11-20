"""Editorial content for the Air Quality Policy section of the Policy Timeline.

This section is a curated reference record of Ireland's air-quality policies. It is
kept separate from the scored greenhouse-gas policy dataset: the entries below are
not given intensity scores and are not rows of the core panel. Dates are legal
commencement or adoption dates taken from the Irish Statute Book, EUR-Lex, gov.ie
and the EPA (checked November 2026). Mechanism keys reuse the dashboard's
instrument types so colours and labels match the rest of the Policy Timeline.
"""

# ---------------------------------------------------------------------------
# Sources cited in this section (key -> (citation, url))
# ---------------------------------------------------------------------------
SOURCES = {
    "APA1987": ("Air Pollution Act 1987 (No. 6 of 1987). Irish Statute Book.",
                "https://www.irishstatutebook.ie/eli/1987/act/6/"),
    "EPAACT1992": ("Environmental Protection Agency Act 1992 (No. 7 of 1992). Irish Statute Book.",
                   "https://www.irishstatutebook.ie/eli/1992/act/7/"),
    "SI326_2012": ("S.I. No. 326/2012, Air Pollution Act (Marketing, Sale, Distribution and Burning of Specified Fuels) Regulations 2012. Irish Statute Book.",
                   "https://www.irishstatutebook.ie/eli/2012/si/326/"),
    "GOV2020": ("Department of the Environment, Climate and Communications (27 July 2020). Minister Ryan signs Regulations to extend Smoky Coal Ban. gov.ie.",
                "https://www.gov.ie/en/department-of-climate-energy-and-the-environment/press-releases/minister-ryan-signs-regulations-to-extend-smoky-coal-ban"),
    "SI529_2022": ("S.I. No. 529/2022, Air Pollution Act 1987 (Solid Fuels) Regulations 2022. Irish Statute Book.",
                   "https://www.irishstatutebook.ie/eli/2022/si/529/"),
    "SI389_2025": ("S.I. No. 389/2025, Air Pollution Act 1987 (Solid Fuels, Moisture Content) (Amendment) Regulations 2025. Irish Statute Book.",
                   "https://www.irishstatutebook.ie/2025/en/si/0389.html"),
    "EPASFR": ("Environmental Protection Agency. Air Pollution Act 1987 (Solid Fuels) Regulations 2022: guidance and registration.",
               "https://www.epa.ie/our-services/licensing/air/solid-fuel-regulations/"),
    "GOVCLEANAIR": ("Department of the Environment, Climate and Communications. Clean Air: policy, strategy and solid fuel regulations. gov.ie.",
                    "https://www.gov.ie/en/department-of-climate-energy-and-the-environment/publications/clean-air/"),
    "CAS2023": ("Government of Ireland (April 2023). Government approves Ireland's first ever Clean Air Strategy. gov.ie.",
                "https://www.gov.ie/en/press-release/aa501-government-approves-irelands-first-ever-clean-air-strategy"),
    "EPACAS2026": ("Environmental Protection Agency (2026). Clean Air Strategy Review: EPA response to the public consultation.",
                   "https://www.epa.ie/publications/EPAC-0126-Clean-Air-Strategy-Review-Consultation-EPA-Response.2026.pdf"),
    "SI180_2011": ("S.I. No. 180/2011, Air Quality Standards Regulations 2011. Irish Statute Book.",
                   "https://www.irishstatutebook.ie/eli/2011/si/180/"),
    "DIR2024_2881": ("Directive (EU) 2024/2881 of 23 October 2024 on ambient air quality and cleaner air for Europe (recast). EUR-Lex.",
                     "https://eur-lex.europa.eu/eli/dir/2024/2881/oj"),
    "DIR2016_2284": ("Directive (EU) 2016/2284 on the reduction of national emissions of certain atmospheric pollutants (NEC Directive). EUR-Lex.",
                     "https://eur-lex.europa.eu/eli/dir/2016/2284/oj"),
    "SI232_2018": ("S.I. No. 232/2018, European Union (National Emission Ceilings) Regulations 2018. Irish Statute Book.",
                   "https://www.irishstatutebook.ie/pdf/2018/en.si.2018.0232.pdf"),
    "EPAAPE2026": ("Environmental Protection Agency (2026). Ireland's Air Pollutant Emissions: Trends and Outlook.",
                   "https://www.epa.ie/publications/monitoring--assessment/climate-change/air-emissions/EPA-Irelands-Air-Pollutant-Emissions-Trends-and-Outlook-2026.pdf"),
    "DIR2010_75": ("Directive 2010/75/EU on industrial emissions (integrated pollution prevention and control). EUR-Lex.",
                   "https://eur-lex.europa.eu/eli/dir/2010/75/oj"),
    "SI595_2017": ("S.I. No. 595/2017, European Union (Medium Combustion Plants) Regulations 2017. Irish Statute Book.",
                   "https://www.irishstatutebook.ie/2017/en/si/0595.html"),
    "EPAMCP": ("Environmental Protection Agency. Medium Combustion Plant registration.",
               "https://www.epa.ie/our-services/licensing/air/medium-combustion-plant"),
    "REG2015_1185": ("Commission Regulation (EU) 2015/1185 on ecodesign requirements for solid fuel local space heaters. EUR-Lex.",
                     "https://eur-lex.europa.eu/eli/reg/2015/1185/oj"),
    "EPANAAQMP": ("Environmental Protection Agency (2017). National Ambient Air Quality Monitoring Programme 2017–2022.",
                  "https://www.epa.ie/publications/monitoring--assessment/air/national-ambient-air-quality-monitoring-programme-2017-2022.php"),
    "EPAAQ2024": ("Environmental Protection Agency (2025). Air Quality in Ireland 2024.",
                  "https://www.epa.ie/publications/monitoring--assessment/air/air-quality-in-ireland-2024.php"),
    "EPANEWS2024": ("Environmental Protection Agency (September 2024). Ireland needs to tackle solid fuel burning and transport emissions to meet Clean Air Strategy ambition and protect public health.",
                    "https://www.epa.ie/news-releases/news-releases-2024/ireland-needs-to-tackle-solid-fuel-burning-and-transport-emissions-to-meet-clear-air-strategy-ambition-and-protect-public-health"),
    "SOE2024": ("Environmental Protection Agency (2024). Ireland's State of the Environment Report 2024, chapter on air quality.",
                "https://epawebapp.epa.ie/ebooks/soe2024/56/"),
    "CLANCY2002": ("Clancy, L., Goodman, P., Sinclair, H. and Dockery, D.W. (2002). Effect of air-pollution control on death rates in Dublin, Ireland: an intervention study. The Lancet, 360(9341), 1210–1214.",
                   "https://doi.org/10.1016/S0140-6736(02)11281-5"),
    "HEI176": ("Dockery, D.W., Rich, D.Q., Goodman, P.G. et al. (2013). Effect of air pollution control on mortality and hospital admissions in Ireland. Health Effects Institute Research Report 176.",
               "https://www.healtheffects.org/publication/effect-air-pollution-control-mortality-and-hospital-admissions-ireland"),
    "WHO2021": ("World Health Organization (2021). WHO global air quality guidelines: particulate matter (PM2.5 and PM10), ozone, nitrogen dioxide, sulfur dioxide and carbon monoxide.",
                "https://www.who.int/publications/i/item/9789240034228"),
    "WWB": ("Department of the Environment, Climate and Communications. Warmth and Wellbeing Scheme. gov.ie.",
            "https://www.gov.ie/en/publication/191db-warmth-and-wellbeing-scheme"),
}


def _refs(*keys):
    return [{"text": SOURCES[k][0], "url": SOURCES[k][1]} for k in keys]


# ---------------------------------------------------------------------------
# Headline figures (shown in the facts strip)
# ---------------------------------------------------------------------------
FACTS = [
    ("1990", "Dublin smoky coal ban, Ireland's first fuel-quality rule for homes"),
    ("2022", "Solid Fuel Regulations: smoky coal and wet wood off the market nationwide"),
    ("2040", "Clean Air Strategy goal: meet the WHO air quality guidelines"),
    ("≈1,700", "premature deaths a year linked to poor air quality (EPA, 2025)"),
    ("115", "air quality monitoring stations reporting in 2024"),
]

# ---------------------------------------------------------------------------
# Milestones (chronological). `ref` is the anchor of the profile below.
# ---------------------------------------------------------------------------
MILESTONES = [
    (1987, "Air Pollution Act 1987 enacted", "National", "framework", "apa"),
    (1990, "Smoky coal ban begins in Dublin (marketing, sale and distribution of bituminous coal)", "National", "standards", "coal"),
    (1992, "EPA Act 1992: EPA licensing of major industry (integrated pollution control)", "National", "practice_regulation", "industry"),
    (1995, "Smoky coal ban extended to Cork", "National", "standards", "coal"),
    (1998, "Ban extended to further cities and towns (1998 and 2000)", "National", "standards", "coal"),
    (2011, "Air Quality Standards Regulations 2011 transpose the Ambient Air Quality Directive 2008/50/EC", "EU → National", "framework", "aqs"),
    (2012, "Consolidated smoky coal regulations add a ban on burning in ban areas", "National", "standards", "coal"),
    (2013, "Industrial Emissions Directive applied through EPA licensing", "EU → National", "practice_regulation", "industry"),
    (2016, "Warmth and Wellbeing Scheme starts: home upgrades for people with chronic respiratory conditions", "National", "subsidies_finance", "cobenefits"),
    (2017, "National Ambient Air Quality Monitoring Programme begins; Medium Combustion Plant Regulations", "National", "information_voluntary", "monitoring"),
    (2018, "National Emission Ceilings Regulations transpose Directive (EU) 2016/2284", "EU → National", "framework", "nec"),
    (2020, "Smoky coal ban covers every town over 10,000 people (13 more towns)", "National", "standards", "coal"),
    (2022, "Solid Fuel Regulations 2022 in force (31 October); EU ecodesign limits for new stoves apply (1 January)", "National / EU", "standards", "solidfuel"),
    (2023, "Clean Air Strategy published (April)", "National", "framework", "cas"),
    (2024, "Revised EU Ambient Air Quality Directive (EU) 2024/2881 adopted, with stricter limits for 2030", "EU", "framework", "aqs"),
    (2026, "Clean Air Strategy interim targets; directive transposition due 11 December; wood moisture limit falls to 20% (1 September)", "National / EU", "framework", "cas"),
    (2030, "Second interim targets; NEC 2030 reduction commitments; new EU limit values", "National / EU", "framework", "nec"),
    (2040, "Clean Air Strategy goal: WHO air quality guideline values", "National", "framework", "cas"),
]

# ---------------------------------------------------------------------------
# Policy profiles (same structure as the Instruments guide)
# ---------------------------------------------------------------------------
PROFILES = [
    {
        "key": "apa",
        "mechanism": "framework",
        "title": "Air Pollution Act 1987",
        "period": "1987 – in force",
        "jurisdiction": "National",
        "instrument": "Act No. 6 of 1987",
        "pollutants": ["Smoke", "SO₂", "PM", "NOx"],
        "sectors": ["Residential", "Industry", "Cross-sectoral"],
        "definition": "Ireland's main air-pollution statute. It gives ministers the power to regulate fuels and emissions and gives local authorities duties and powers to prevent and limit air pollution.",
        "rationale": "In the 1980s winter smog from coal fires was a serious public-health problem in Dublin. Government needed a legal basis to control the fuels sold to households and the emissions from industrial premises.",
        "ireland": "Almost every later Irish fuel rule is made under this Act, from the 1990 Dublin smoky coal ban to the Solid Fuel Regulations 2022. Local authorities enforce it through inspections of fuel retailers and distributors and through fixed-penalty notices.",
        "health": "The Act does not set health targets itself. Its value lies in the regulations it enables, which address smoke and fine particles from home heating, the largest source of PM2.5 exposure in Irish towns.",
        "status": "In force and amended many times. The Clean Air Strategy (2023) commits to reviewing air-quality legislation, including a possible new Clean Air Act.",
        "inpact": "Framework layer: comparable in role to the Climate Action Acts in the greenhouse-gas dataset.",
        "refs": _refs("APA1987", "CAS2023"),
    },
    {
        "key": "coal",
        "mechanism": "standards",
        "title": "Smoky coal ban (low smoke zones)",
        "period": "1990 – 2022, then nationwide",
        "jurisdiction": "National",
        "instrument": "Regulations under the Air Pollution Act 1987; consolidated as S.I. No. 326/2012 and extended in 2013–2020",
        "pollutants": ["Black smoke", "PM2.5", "PM10", "SO₂"],
        "sectors": ["Residential heating"],
        "definition": "A ban on the marketing, sale and distribution of bituminous (smoky) coal in designated low smoke zones. From 2012 it was also an offence to burn smoky coal in those zones.",
        "rationale": "Before 1990 about 80% of Dublin's winter smog came from burning bituminous coal in open fires. Restricting what can be sold targets the source of the smoke without regulating each home's heating directly.",
        "ireland": "The ban began in Dublin on 1 September 1990. It was extended to Cork in 1995 and to other cities and large towns in 1998 and 2000, and in stages through 2011–2013. From 1 September 2020 it covered every town with more than 10,000 people, after 13 towns were added. The Solid Fuel Regulations 2022 replaced the zone system with one nationwide standard.",
        "health": "Black smoke in Dublin fell by about 70% after the ban. Clancy et al. (2002) found that, in the six years after the ban, age-standardised respiratory deaths fell by 15.5% and cardiovascular deaths by 10.3%. They estimated about 116 fewer respiratory and 243 fewer cardiovascular deaths a year. A later study for the Health Effects Institute re-analysed Dublin and the bans in 11 other cities. It confirmed the falls in black smoke and in respiratory deaths; the earlier cardiovascular result was not clearly reproduced once long-term national trends were allowed for.",
        "status": "Superseded on 31 October 2022 by the nationwide Solid Fuel Regulations.",
        "inpact": "Coal burned at home also emits CO₂. The ban and the 2013 extension of the carbon tax to solid fuels both push households from coal towards cleaner fuels.",
        "refs": _refs("SI326_2012", "GOV2020", "CLANCY2002", "HEI176"),
    },
    {
        "key": "solidfuel",
        "mechanism": "standards",
        "title": "Solid Fuel Regulations 2022",
        "period": "31 October 2022 – in force",
        "jurisdiction": "National",
        "instrument": "S.I. No. 529/2022, amended by S.I. No. 76/2025 and S.I. No. 389/2025",
        "pollutants": ["PM2.5", "Smoke", "SO₂"],
        "sectors": ["Residential heating", "Fuel supply"],
        "definition": "One national standard for every solid fuel offered for sale: coal, manufactured fuels, wood, peat briquettes and turf. The same rules apply in towns and in the countryside.",
        "rationale": "By 2020 solid-fuel burning in homes was the main source of fine-particle pollution in Ireland, including in small towns outside the low smoke zones. A single standard closes the gaps between zones and also covers wet wood, a large source of smoke.",
        "ireland": "Coal products and manufactured fuels must have a smoke emission rate below 10 g per hour, which in effect ends the sale of smoky coal nationwide. Part-biomass manufactured fuels must be below 5 g per hour. Wood sold in units of 2 m³ or less must have a moisture content below 25%; this limit falls to 20% from 1 September 2026 (S.I. No. 389/2025). Larger loads of wood must come with drying instructions. The commercial sale and advertising of turf is restricted, with limited exceptions for people with turbary rights. The 2% sulphur limit for coal and manufactured fuels remains until 1 September 2030 at the latest (S.I. No. 76/2025). Fuel producers register with the EPA; local authorities enforce the rules at retail level.",
        "health": "The regulations target PM2.5, the pollutant most strongly linked to heart and lung disease. The EPA reports that PM2.5 from solid fuel in homes remains the main air-quality concern in Irish towns, so the effect of these rules is a direct health question.",
        "status": "In force. Phased limits run to 2026 (wood moisture) and 2030 (sulphur).",
        "inpact": "These rules sit in the same homes and the same years as the building-energy and heating policies in the greenhouse-gas dataset. Separating their effects needs care.",
        "refs": _refs("SI529_2022", "SI389_2025", "EPASFR", "GOVCLEANAIR"),
    },
    {
        "key": "cas",
        "mechanism": "framework",
        "title": "Clean Air Strategy",
        "period": "April 2023 – 2040",
        "jurisdiction": "National",
        "instrument": "Government strategy (Department of the Environment, Climate and Communications)",
        "pollutants": ["PM2.5", "PM10", "NO₂", "SO₂", "O₃"],
        "sectors": ["Cross-sectoral"],
        "definition": "Ireland's first national clean air strategy. It sets the long-term goal of meeting the World Health Organization's 2021 air quality guideline values by 2040, with interim targets for 2026 and 2030.",
        "rationale": "Ireland meets the current EU legal limits, but monitored levels are above the WHO's health-based guidelines for several pollutants. A strategy gives a target path beyond legal compliance and coordinates action across government.",
        "ireland": "The interim targets follow the WHO interim targets 3 (2026) and 4 (2030). The strategy includes a review of air-quality legislation and a possible new Clean Air Act. It set up a Clean Air Strategic Implementation Group and a communications group, with an annual progress report to Government. In 2026 the EPA recommended aligning the 2026 and 2030 targets with the new EU limit values while keeping the 2040 WHO goal.",
        "health": "The WHO guideline for annual PM2.5 is 5 µg/m³; interim target 4 is 10 µg/m³. The EPA's 2024 assessment found Ireland was not on track to meet the 2026 interim targets for PM2.5, PM10, NO₂, SO₂ and ozone. It named solid-fuel burning and road traffic as the sources to tackle.",
        "status": "In force; under review in 2026.",
        "inpact": "The strategy's targets give a natural benchmark for the air-quality outcomes of climate policies, in the same way as the 2030 and 2050 climate targets do for emissions.",
        "refs": _refs("CAS2023", "EPACAS2026", "EPANEWS2024", "WHO2021"),
    },
    {
        "key": "aqs",
        "mechanism": "framework",
        "title": "Ambient air quality standards",
        "period": "2011 – in force; revised directive for 2030",
        "jurisdiction": "EU → National",
        "instrument": "S.I. No. 180/2011 (Directive 2008/50/EC); Directive (EU) 2024/2881",
        "pollutants": ["PM2.5", "PM10", "NO₂", "SO₂", "O₃", "CO", "Benzene"],
        "sectors": ["Cross-sectoral"],
        "definition": "Legally binding limit values for the concentration of pollutants in outdoor air, with duties to monitor, assess, inform the public and act where limits are exceeded.",
        "rationale": "Concentration limits protect people where they live and breathe, whatever the source. They make the State accountable for air quality across the whole country.",
        "ireland": "The Air Quality Standards Regulations 2011 took effect on 12 April 2011 and transpose Directive 2008/50/EC. The EPA runs the national assessment and reports to the European Commission. The recast Directive (EU) 2024/2881 sets stricter limits from 2030, much closer to the WHO guidelines (for example an annual limit of 10 µg/m³ for PM2.5). It must be transposed by 11 December 2026.",
        "health": "Ireland met all EU limits in 2024. Against the 2030 limits, the EPA projects only partial compliance: about 93% for PM2.5 and 78% for NO₂.",
        "status": "In force; transposition of the 2024 directive is due by December 2026.",
        "inpact": "Limit values apply to concentrations, while the INPACT dataset tracks emissions. Monitoring data link the two.",
        "refs": _refs("SI180_2011", "DIR2024_2881", "EPAAQ2024"),
    },
    {
        "key": "nec",
        "mechanism": "framework",
        "title": "National Emission Ceilings",
        "period": "2001 – in force; 2030 commitments",
        "jurisdiction": "EU → National",
        "instrument": "Directive (EU) 2016/2284; S.I. No. 232/2018",
        "pollutants": ["SO₂", "NOx", "NMVOC", "NH₃", "PM2.5"],
        "sectors": ["Agriculture", "Transport", "Residential", "Energy", "Industry"],
        "definition": "National caps on total yearly emissions of five air pollutants, set as percentage cuts from 2005 levels for 2020 and for 2030.",
        "rationale": "Air pollution crosses borders and forms secondary particles from ammonia, NOx and SO₂. National totals cap the overall load, complementing local concentration limits.",
        "ireland": "Ireland's 2030 commitments, compared with 2005, are cuts of 85% for SO₂, 69% for NOx, 32% for NMVOC, 5% for ammonia and 41% for PM2.5. The 2018 regulations also require a national air pollution control programme. Ammonia, almost all from agriculture, exceeded its 2020 ceiling for several years. The EPA's 2026 outlook projects compliance in 2030 for SO₂, NOx, ammonia and PM2.5, with NMVOC remaining a challenge.",
        "health": "Ammonia from agriculture forms secondary PM2.5 far from its source, so emission totals matter for health even where local concentrations look low.",
        "status": "In force.",
        "inpact": "This is the closest air-quality counterpart to Ireland's sectoral emission ceilings for greenhouse gases. The agricultural measures in the GHG dataset, such as low-emission slurry spreading, also cut ammonia.",
        "refs": _refs("DIR2016_2284", "SI232_2018", "EPAAPE2026"),
    },
    {
        "key": "industry",
        "mechanism": "practice_regulation",
        "title": "Industrial and combustion plant licensing",
        "period": "1994 – in force",
        "jurisdiction": "EU → National",
        "instrument": "EPA Act 1992 (integrated pollution control); Directive 2010/75/EU; S.I. No. 595/2017 (medium combustion plants)",
        "pollutants": ["SO₂", "NOx", "PM", "Dust"],
        "sectors": ["Industry", "Electricity"],
        "definition": "Permits that set emission limit values and best-available-technique requirements for power stations, large industry and, since 2018, medium combustion plants of 1–50 MW thermal input.",
        "rationale": "Large point sources are few, easy to identify and can be controlled at the stack. Licensing places the duty on the operator and lets the regulator tighten limits as technology improves.",
        "ireland": "The EPA has licensed major industrial activities under the EPA Act 1992 since the mid-1990s. The Industrial Emissions Directive was applied through these licences from 2013. The Medium Combustion Plant Regulations, signed in December 2017, require registration and emission limits for boilers and generators of 1–50 MW that are not already licensed.",
        "health": "Point-source controls drove most of the large fall in Ireland's SO₂ emissions since 1990, together with the move away from coal and heavy fuel oil.",
        "status": "In force.",
        "inpact": "Most licensed plants are also in the EU Emissions Trading System, so the same installations appear in both policy records.",
        "refs": _refs("EPAACT1992", "DIR2010_75", "SI595_2017", "EPAMCP"),
    },
    {
        "key": "stoves",
        "mechanism": "standards",
        "title": "Ecodesign limits for solid fuel stoves",
        "period": "1 January 2022 – in force",
        "jurisdiction": "EU",
        "instrument": "Commission Regulation (EU) 2015/1185",
        "pollutants": ["PM", "NOx", "CO", "OGC"],
        "sectors": ["Residential heating"],
        "definition": "EU-wide minimum efficiency and maximum emissions of particulate matter, organic gaseous compounds, carbon monoxide and NOx for new solid fuel local space heaters (stoves) of up to 50 kW.",
        "rationale": "The appliance matters as much as the fuel: older stoves and open fires emit far more particles per unit of heat. Setting limits for new products raises the standard of the stock as appliances are replaced.",
        "ireland": "The limits apply to stoves placed on the Irish market from 1 January 2022. They complement the Solid Fuel Regulations, which control the fuel, and Part L of the Building Regulations, which reduces how much heat a home needs.",
        "health": "Effects build up slowly, because they only apply to new appliances. Existing open fires and old stoves are not covered.",
        "status": "In force.",
        "inpact": "Appliance standards of this type already appear in the GHG dataset (for example minimum energy-performance standards for appliances).",
        "refs": _refs("REG2015_1185"),
    },
    {
        "key": "monitoring",
        "mechanism": "information_voluntary",
        "title": "National air quality monitoring programme",
        "period": "2017 – in force",
        "jurisdiction": "National",
        "instrument": "EPA National Ambient Air Quality Monitoring Programme 2017–2022 and its successors",
        "pollutants": ["PM2.5", "PM10", "NO₂", "SO₂", "O₃"],
        "sectors": ["Cross-sectoral"],
        "definition": "A greatly expanded national network of monitoring stations and air quality modelling, with real-time public information.",
        "rationale": "Policy needs evidence. Before 2017 monitoring was concentrated in a few cities; smaller towns, where solid-fuel smoke is often worst, were hardly measured.",
        "ireland": "The programme began at the end of 2017. The network grew from about 30 stations in 2017 to 115 stations reporting in 2024. Readings are published hourly on airquality.ie, with a three-day forecast and an Air Quality Index for Health.",
        "health": "The expanded network showed that winter PM2.5 in many small towns is above the WHO guidelines, which shaped the move to nationwide fuel rules.",
        "status": "Ongoing.",
        "inpact": "Monitoring data are the obvious next layer for the INPACT platform, to link policy timing with measured air quality.",
        "refs": _refs("EPANAAQMP", "EPAAQ2024", "SOE2024"),
    },
]

# ---------------------------------------------------------------------------
# Greenhouse-gas policies in the INPACT dataset with air-quality effects.
# (policy_id, sector) are looked up to link to the existing policy pages.
# effect: "co" = co-benefit, "mixed" = depends on technology, "trade" = trade-off
# ---------------------------------------------------------------------------
COBENEFITS = [
    ("CAPMF_PARTL_RES", "Buildings", "co", "PM2.5, NOx",
     "Successive Part L standards cut the heat a new home needs. Since the NZEB standard (2019), most new homes use heat pumps rather than solid fuel or oil."),
    ("IRL_P0017", "Buildings", "co", "PM2.5, NOx",
     "Insulation and heating upgrades reduce the fuel burned in existing homes."),
    ("IRL_P0013", "Buildings", "co", "NOx, CO",
     "Efficient condensing boilers burn less oil and gas for the same heat."),
    ("IRL_P0005", "Buildings", "co", "PM2.5, SO₂",
     "Solid fuels (coal and peat) were brought into the carbon tax from 2013, raising their price relative to cleaner options."),
    ("IRL_P0028", "Buildings", "mixed", "PM2.5",
     "Heat pumps and solar thermal remove combustion at home; biomass boilers and stoves can add fine particles."),
    ("RES_Buildings", "Buildings", "co", "PM2.5, NOx",
     "Includes Warmer Homes, Greener Homes, the National Home Energy Upgrade Scheme, heat pump grants and the Warmth and Wellbeing Pilot, which upgraded homes of people with chronic respiratory conditions."),
    ("IRL_P0018", "Transport", "co", "NO₂, PM",
     "Electric vehicles have no exhaust emissions; brake, tyre and road-wear particles remain."),
    ("IRL_P0019", "Transport", "trade", "NO₂",
     "The 2008 CO₂-based vehicle taxes are widely reported to have shifted car buyers towards diesel, which emits more NOx in real driving."),
    ("IRL_P0020", "Transport", "mixed", "NO₂",
     "Fleet CO₂ targets favoured efficient diesel cars at first; the shift to electric cars now cuts NO₂ as well."),
    ("CAPMF_EU_ETS", "Electricity", "co", "SO₂, NOx, PM",
     "Carbon pricing speeds the closure of coal and peat power stations, which were major SO₂ and NOx sources."),
]

EFFECT_LABELS = {
    "co": ("Co-benefit", "#2F7D4A"),
    "mixed": ("Depends on technology", "#A6611A"),
    "trade": ("Trade-off", "#B03A2E"),
}

CAVEATS = [
    ("A reference record, not a scored dataset.", " The air-quality policies are not part of the 2000–2023 greenhouse-gas panel. They have no intensity scores and do not appear in the Timeline, Policies or OECD scores sections."),
    ("Dates are legal dates.", " Years are commencement, adoption or publication dates from official sources, not modelled implementation profiles."),
    ("Association is not causation.", " Air quality also changes with weather, fuel prices, the economy and other policies. Studies such as the Dublin coal ban evaluations adjust for these factors; the timeline alone does not."),
    ("Rules are still changing.", " The EU directive is due to be transposed by December 2026, the Clean Air Strategy is under review, and some solid-fuel limits phase in to 2030. Check the official sources for the current position."),
]
