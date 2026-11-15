# Policy Timeline tab: content verification and corrections

Date: 15 November 2026. Scope: every piece of explanatory text in the Policy Timeline tab (instrument guide, policy summaries, milestones, page wording, references) and the sources it cites. This follows the audit of 31 October 2026 (`POLICY_TIMELINE_AUDIT.md`), most of whose wording findings had not been applied.

**No date, score or selection in the dataset was changed in this pass, with one later exception: the LIEN start year (section 7).** Only wording, milestones, notes and reference metadata changed. A before/after comparison of the database confirms that the only columns that differ are `description`, dictionary `definition`, method `decision` and one reference `publication_date`.

## 1. How the check was done

| Source type | How it was read | Result |
| --- | --- | --- |
| Irish Statute Book (2 Acts, 9 statutory instruments) | Full text fetched and searched | All opened |
| gov.ie, EPA, Revenue, European Commission, NORA pages | Full text fetched and searched | All opened |
| Revenue excise duty rates manual (October 2026 edition) | PDF text extracted | Full rate history read |
| EPA final inventory 1990–2024 (March 2026) | PDF text extracted | Table 4 read |
| SEAI and OECD pages (block automated fetches) | Opened in a browser | Opened |
| EUR-Lex | Not opened (returns a challenge page) | EU dates checked through Commission pages instead |

Link check: 44 cited links were tested. All resolve. Two redirect to a new address and still work. `http://www.seai.ie/eeos/` and the SEAI and OECD pages refuse automated requests but open in a browser.

## 2. Claims verified as correct

| Claim on the site | Source | Result |
| --- | --- | --- |
| Climate Act 2015 enacted 10 December 2015; annual transition statements | Act No. 46 of 2015 | Correct |
| Advisory Council established 18 January 2016 | S.I. 25/2016 | Correct |
| Amendment Act enacted 23 July 2021 | Act No. 32 of 2021 | Correct |
| 51% reduction by 2030 against 2018 | Act 2021, carbon-budget provision | Correct, but it is a requirement on the first two carbon budgets |
| Carbon-budget programme took effect 6 April 2022 | gov.ie Carbon Budgets | Correct |
| Sectoral ceilings agreed 28 July 2022 | gov.ie Sectoral Emissions Ceilings | Correct |
| Section 21 restricts new petroleum authorisations, with saving provisions | Act 2021 s.21; gov.ie | Correct |
| Carbon tax: €15 from December 2009 (motor fuels), 1 May 2010 (other liquid fuels, gas); €20 on 7 December 2011 and 1 May 2012; €26 on 9 October 2019 and 1 May 2020; €33.50, €41, €48.50 on 1 May 2021–2023 | Revenue rates manual | Correct |
| EU ETS from 2005; aviation from 2012 | EPA | Correct |
| Part L NZEB for non-dwellings applies from 2019 | S.I. 538/2017 | Correct (1 January 2019) |
| Energy audits: first deadline December 2015, four-year cycle | S.I. 426/2014 | Correct (5 December 2015) |
| Landfill levy 2002 | S.I. 86/2002 | Correct (1 June 2002, €15 per tonne) |
| MAC Directive: 2011 new types, 2017 all new vehicles | European Commission | Correct |
| Motors: Regulation 640/2009, replaced by 2019/1781 from 1 July 2021 | European Commission | Correct |
| Biofuels obligation from 2010 | NORA | Correct (1 July 2010) |
| REFIT from 2006; first RESS auction 2020 | gov.ie | Correct |
| Renewables 41.0% of electricity generated in 2023 | EPA report and key messages | Correct |
| 2023 emissions: total 54.992 Mt; all eight sector values | EPA final inventory, Table 4 | All correct |
| CAPMF: 130 variables, 56 policies, 1990–2023 | OECD explainer and documentation | Correct |
| LIEN members spend €1 million or more on energy | SEAI | Correct |

The 16 literature references were checked against known publication details (authors, year, journal, volume, pages). No errors were found. This check was from bibliographic knowledge, not from each publisher's page.

## 3. Problems found and corrected

| # | Where | Problem | Correction |
| --- | --- | --- | --- |
| 1 | Instrument guide, carbon pricing | "Non-transport fuels followed in May 2010" wrongly included solid fuels | Named the fuels; solid fuels added at €10 on 1 May 2013 and €20 on 1 May 2014 |
| 2 | Instrument guide and carbon-tax milestones | "Annual increases of €7.50 towards €100" | Final step is €6.50; motor-fuel steps each October added; noted that the 2026 increases were postponed to 1 May 2027 |
| 3 | Carbon-tax milestones | 2021–2023 showed only the May changes | October motor-fuel rates added (€41, €48.50, €56) |
| 4 | Sectoral ceilings summary | "for each sector of the economy" | "specified sectors"; land-use ceiling was deferred |
| 5 | 2021 Act | Enactment only | Commencement on 7 September 2021 (S.I. 468/2021) added |
| 6 | 2015 Act summary | Said the Act "established" the Council | Act provided for it; established 18 January 2016 |
| 7 | Instrument guide, standards | "They must also carry a CO₂ label" (subject unclear) | Rewritten; Irish transposition S.I. 339/2001 added |
| 8 | Appliance standards summary | Called 1996 rules "ecodesign" | Ecodesign Directives date from 2005; wording corrected |
| 9 | MAC milestone | "all newly registered cars" | Passenger cars and light vans (N1, class I) |
| 10 | Motors milestones | Successor regulation missing | 2021 and 2023 steps added |
| 11 | Every open-ended profile | "in force since [year]" although many start years are not legal dates | "recorded from [year]"; status definition changed to match |
| 12 | Profiles of EEA-derived policies | EEA text shown as if it were the site's own description | Now labelled as the description reported to the EEA, with scenario assumptions flagged |
| 13 | Selection label | "Top-impact" implied proven effect | "Largest reported savings" |
| 14 | OECD scores page | Level 2 described wrongly; score of 10 unexplained | 15 modules described; 10 explained as relative |
| 15 | About page | Claimed legal commencement dates "were verified" for all policies | Rewritten to say what was checked and that many start years follow the EEA record or the OECD proxy |
| 16 | About page | 90% rule stated without the land-use exception | Exception added |
| 17 | Methods page and data dictionary | Coverage described as "legal" scope; flag M as "not applicable" | Both corrected |
| 18 | Reference list | SEAI LIEN page dated 2019 | 2018 (page is dated 21 November 2018) |
| 19 | LIEN text | No founding date | "launched in 1995" added |
| 20 | Profile reference link | Two policies had two links joined in one broken link | Split into separate links |

## 4. Verification notes added to profiles

28 policy families now carry a "Verification notes" panel where an official source differs from, or qualifies, the record. The main ones:

| Policy | Note |
| --- | --- |
| Large Industry Energy Network | Launched 1995; dataset starts 2000 |
| Renewable electricity (REFIT/RESS) | EEA text attributes the 70% target to the 2021 Plan; it was set in 2019 and raised to up to 80% in 2021. Start 2005 precedes REFIT 1 (2006) |
| Accelerated Capital Allowance | A Revenue tax relief, not an SEAI scheme |
| EU CO₂ car standards | "Expired in 2019" refers to the replaced regulation only |
| Landfill Directive | 1999 is adoption, not when obligations applied in Ireland |
| Boiler regulation, VRT and motor tax | End years are the end of a reported phase, not repeal |
| Biofuels | 2005 reflects excise relief; the obligation began 1 July 2010 |
| Car labels, appliance labels and standards, Part L | Start years are OECD first-positive years, not Irish commencement |
| Residual bundles | Member dates that differ from official sources (below) |

## 5. Open items that need your decision

These affect dataset dates and therefore scores. They are flagged on the site but not changed.

| Policy | Dataset | Official source | Checked today? |
| --- | --- | --- | --- |
| Large Industry Energy Network | starts 2000 | launched 1995 (SEAI) | Yes. **Corrected to 1995 on 15 November 2026, see section 7** |
| ReHeat programme | starts 2008 | launched March 2007 | No, carried from the 31 October audit |
| SEEEP/EERF/Better Energy Workplaces | ends 2010 | still operating 2011 | No, carried over |
| Solar PV pilot | starts 2019 | opened 31 July 2018 | No, carried over |
| Smart-meter roll-out | starts 2021 | began late 2019 | No, carried over |
| National Home Energy Upgrade Scheme | starts 2021 | launched February 2022 | No, carried over |
| CHP deployment | ends 2011 | SEAI describes 2006–2010 | No, carried over |

Other limits:

- The notes on Better Energy Homes (2009 predecessor), the electric-vehicle grant (2011), the Public Sector Programme and the peatlands funding date rest on the earlier audit's evidence and general knowledge. They were not re-opened today.
- EUR-Lex texts were not opened. EU regulation dates rest on European Commission summary pages and, for Regulation 443/2009 phase-in percentages and Directive adoption dates, on general knowledge.
- S.I. 259/2008 is cited as "in operation from July 2008"; the day was not confirmed.
- The original EEA descriptions are reproduced unedited by design. Errors in them are flagged in notes, not rewritten.

## 6. Files changed

`policies/editorial.py`, `policies/glossary.py`, `policies/services.py`, `policies/views.py`, `policies/static/policies/js/method.js`, six templates in `policies/templates/policies/`, and the rebuilt `data/policy_timeline/policy_timeline.sqlite3`.

Checks after the change: database reloaded (47 series, 1,128 rows), 7 of 7 policy tests pass, all 47 profile pages and the Methods and Instruments pages load in a browser.

## 7. Addendum: LIEN start year corrected to 1995

Approved and applied on 15 November 2026. This is the one change to dataset values; it supersedes the statement at the top that no date or score was changed.

| Item | Before | After |
| --- | --- | --- |
| Start year (IRL_P0001, Industry) | 2000 | 1995 |
| Implementation level, 2000 | 0.25 | 1 |
| Implementation level, 2001 | 0.75 | 1 |
| Policy intensity, 2000 | 0.03125 | 0.125 |
| Policy intensity, 2001 | 0.09375 | 0.125 |
| 2002–2023 | unchanged | unchanged |

The values follow the release's own assumed-timing rule for information and voluntary programmes (no lag, two-year linear ramp from mid-year of the start year). The equal-weight indices for 2000 and 2001 change accordingly. The row now carries the `source_date_conflict` flag, and its start-date basis names SEAI as the source and records that the EEA reports 2000.

Files changed: `ireland_core_policy_timeline.csv` (24 rows), `policy_catalogue.csv` (1 row), `selection_log.csv` (selected start year only; the EEA-reported start year stays 2000), and the rebuilt database. LIEN is not a member of any residual bundle, so no other series changes. The release consistency script reports no discrepancies after the change, and the 7 policy tests pass.

The audit outputs of 31 October in this folder (`policy_register.csv`, `local_series_payload.json` and others) still show the 2000 start, because they are the record of that audit.
