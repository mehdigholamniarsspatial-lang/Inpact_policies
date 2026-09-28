# INPACT: Ireland GHG Policy Impact Explorer and Climate Policy Timeline

A Django platform for the **INPACT** project (*Investigating National Policy
Impacts on Atmospheric Climate Targets*, funded by the EPA). It brings three
tools together in one tabbed dashboard:

* the **Ireland Greenhouse Gas Policy Impact Explorer**: emissions, maps,
  policy intelligence and trend analysis;
* the **Ireland Climate Policy Timeline**: a detailed record of 34 core
  mitigation policy families (47 policy–sector series, 2000–2023), built from
  OECD CAPMF and EEA policies-and-measures data;
* project information and a public **feedback** form.

It is built to run locally or on Vercel's zero-configuration Django runtime
(see [Deployment](#deployment) for the size caveats).

---

## Contents

1. [Quick start](#quick-start)
2. [The dashboard at a glance](#the-dashboard-at-a-glance)
3. [Project layout](#project-layout)
4. [Explorer tab](#explorer-tab)
5. [Policy Timeline tab](#policy-timeline-tab)
6. [Trend Analysis tab](#trend-analysis-tab)
7. [Structural Break Analysis tab](#structural-break-analysis-tab)
8. [About INPACT tab](#about-inpact-tab)
9. [Feedback tab](#feedback-tab)
10. [Editing the data](#editing-the-data)
11. [URL and API reference](#url-and-api-reference)
12. [Configuration (environment variables)](#configuration-environment-variables)
13. [Testing](#testing)
14. [Deployment](#deployment)

---

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py runserver
```

Open http://127.0.0.1:8000.

No database setup is needed. The Policy Timeline ships with a pre-built,
read-only SQLite file, and every other tab reads CSV files directly.

Useful starting links:

| Link | Opens |
|---|---|
| http://127.0.0.1:8000/ | Explorer tab |
| http://127.0.0.1:8000/#policy | Policy Timeline tab, Overview |
| http://127.0.0.1:8000/#policy/timeline/ | Policy Timeline tab, Timeline view |
| http://127.0.0.1:8000/policy/ | The Policy Timeline on its own, with its original header |

---

## The dashboard at a glance

A tab bar sits directly under the INPACT / EPA header:

| Tab | What it is | Where the code lives |
|---|---|---|
| **Explorer Dashboard** | Filters sidebar, emissions time series (inventory and Sector Explorer modes), satellite map with raster overlays, Policy Intelligence Panel, Climate Policy Roadmap, climate-target cards | `explorer/page/index.html`, `explorer/views.py`, `explorer/rasters.py` |
| **Policy Timeline** | The full *Ireland Climate Policy Timeline* dashboard, with all eight sections and every policy profile | `policies/` app, mounted at `/policy/` |
| **Trend Analysis** | Piecewise regression, Mann–Kendall and Sen's slope on sectoral emissions | `explorer/trend_engine.py`, `explorer/trend_views.py` |
| **Structural Break Analysis** | Description of, and launcher for, the companion Streamlit app | `explorer/page/index.html` |
| **About INPACT** | Mission, approach, data sources and team | `explorer/page/index.html`, `explorer/static/img/` |
| **Feedback** | Public-participation form saved to an Excel workbook | `explorer/feedback_store.py` |

---

## Project layout

```
INPACT_Combined/
├── manage.py
├── requirements.txt
├── README.md
├── data/
│   ├── ghg_inventory.csv          # national emissions by gas (Explorer chart + KPIs)
│   ├── policies.csv               # roadmap policies (Explorer chart markers, roadmap, intelligence panel)
│   ├── sector_inventory/          # Total/CO2/CH4/N2O by sector (Sector Explorer + Trend Analysis)
│   ├── Raster/                    # GeoTIFF emission grids  <Year>_<Sector>_<Parameter>.tif
│   ├── RasterPrerendered/         # PNG + JSON overlays pre-rendered from Raster/ (used on Vercel)
│   └── policy_timeline/           # Policy Timeline release files
│       ├── ireland_core_policy_timeline.csv   # main dataset (policy × sector × year)
│       ├── policy_catalogue.csv, selection_log.csv, overlap_register.csv, …
│       ├── config/ qa/ raw/ reference/        # scoring config, QA evidence, raw OECD/EEA inputs
│       └── policy_timeline.sqlite3            # pre-built read-only database
├── inpact_platform/               # Django project: settings, root URLs, WSGI/ASGI
├── explorer/                      # INPACT Explorer app
│   ├── page/index.html            # the single-page dashboard (all tabs, CSS and JS inline)
│   ├── views.py                   # serves the page, injects CSV data, raster + feedback APIs
│   ├── rasters.py                 # GeoTIFF → coloured PNG overlays
│   ├── trend_engine.py            # regression / trend statistics
│   ├── trend_views.py             # Trend Analysis JSON API
│   ├── feedback_store.py          # feedback → Excel (local disk or GitHub)
│   ├── static/img/                # logos and team photos
│   └── test_trend_analysis.py
├── policies/                      # Ireland Climate Policy Timeline app (/policy/)
│   ├── models.py                  # PolicySeries, PolicyYear, SelectionCandidate, CAPMF, EEA, …
│   ├── views.py, urls.py          # pages, JSON API, CSV export
│   ├── services.py                # query helpers that build the JSON payloads
│   ├── glossary.py                # plain-language definitions and colours (drives tooltips)
│   ├── editorial.py               # curated text: instrument guide, milestones, literature, …
│   ├── management/commands/load_policy_data.py   # CSV/XLSX → database importer
│   ├── templates/policies/        # page templates (base.html handles the embedded mode)
│   ├── static/policies/           # CSS, page scripts, vendored Plotly and D3
│   └── tests.py
└── scripts/
    └── prerender_rasters.py       # builds data/RasterPrerendered/ from data/Raster/
```

---

## Explorer tab

The main analytical dashboard.

* **Filters and selections (sidebar):** indicator (Total GHG, CO₂, CH₄, N₂O, …),
  time-series mode (national inventory or **Sector Explorer**, Main Sector →
  Subsector), year range, and **Policy Interventions** checkboxes by
  jurisdiction.
* **2A Time-Series Emissions Analysis:** observed emissions from the CSV data,
  plus a no-policy baseline, a policy-adjusted pathway, a forecast and a 95%
  confidence band. These are computed from the observed values by the model in
  `index.html`. Policy guide-lines are annotated on the chart.
* **2B Spatial Environmental Mapping:** Esri World Imagery satellite base map
  (no API key needed; needs an internet connection). Raster emission overlays
  are chosen with cascading **Year → Sector → Parameter** dropdowns. The station
  markers are illustrative placeholders.
* **3 Policy Intelligence Panel:** details of the selected roadmap policy. The
  **Open its profile in the Policy Timeline** button goes straight to the
  matching policy in the Policy Timeline tab. Matching is by name. When there
  is no match, the button reads *Explore all policies in the Policy Timeline*
  and opens its Timeline view.
* **4 Climate Policy Roadmap, 1992 → 2050:** click a node to inspect it. The
  **Detailed timeline** link opens the Policy Timeline's year-by-year view.

### Raster overlays

Put GeoTIFFs in `data/Raster/`, named `<Year>_<Sector>_<Parameter>.tif`. For
example, `2019_B_Industry_pbenzoA.tif` gives Year `2019`, Sector `B_Industry` and
Parameter `pbenzoA`. The year is the first token and the parameter is the last;
everything in between is the sector. The folder is re-scanned on every request.

Each overlay is reprojected to Web-Mercator (sources may be Irish Grid,
EPSG:29902). It uses a **rainbow** colour map on a **log** scale between the 2nd
and 98th percentiles. Zero and nodata cells are transparent, and a matching
colour-bar legend is drawn. An all-zero raster is reported rather than drawn.

**Live vs. pre-rendered.** Live rendering needs `rasterio` (GDAL), which is
optional and not installable on Vercel. Without it, `explorer/rasters.py` serves
the committed PNG + JSON files in `data/RasterPrerendered/`. After adding or
changing a `.tif`:

```bash
pip install "rasterio>=1.3,<2"          # local machine only, once
python scripts/prerender_rasters.py
git add data/RasterPrerendered && git commit -m "Update raster overlays"
```

---

## Policy Timeline tab

The *Ireland Climate Policy Timeline*, formerly the standalone
`irl_policy_dashboard` project, is merged in as the Django app **`policies/`**.
It is mounted at **`/policy/`** and shown inside the **Policy Timeline** tab.
Its structure is preserved: every page, chart, filter, tooltip, quick-view
drawer, policy profile, API and download works as in the original.

### What it contains

The dataset combines the OECD **Climate Actions and Policies Measurement
Framework (CAPMF)** with the **EEA database of national policies and measures
(PaMs)**. It covers 34 core policy families and 5 residual sector bundles,
which make 47 policy–sector series over 2000–2023 (1,128 rows, 67 columns).

| Section | What it shows |
|---|---|
| **Overview** | A "policy river" of all 47 series, how the dataset was built, a clickable sector × mechanism matrix, the four policy layers, policies in force over time, and where implementation values come from. |
| **Timeline** | The main view. An **intensity grid** (intensity, implementation, OECD stringency or equal-weight index) or a **lifespan** view. Group by sector, mechanism, layer or source, with filters, search and sorting. A year slider with play, and hatching for assumed-timing years. Click a row for a quick-view drawer. |
| **Categories** | Sunburst or treemap across four hierarchies, a guide to every mechanism and sector, the coverage and bindingness scoring ladders, a scope-vs-bindingness scatter, and a "try the formula" widget. |
| **Instruments** | A guide to each policy mechanism: definition, economic rationale, use in Ireland, strengths, limitations, how it is measured, its policies and key literature. |
| **Policies** | A searchable, sortable table of all series with sparklines (CSV export of the filtered rows on the standalone site only). |
| **Policy profile** | For each series: description, a year-by-year chart with status bands and OECD-vs-assumed markers, an intensity breakdown, classification, scores with rationales, OECD link, EEA records, overlaps, data-quality flags and citations. |
| **OECD scores** | A heatmap of all 56 CAPMF level-3 categories (1990–2023), a comparison chart for any level-3 or level-4 indicator, and the eligibility decision for each category. |
| **Methods** | Selection-flow Sankey, the scoring model, all 115 candidates with the five eligibility tests, the 90% materiality rule, an interactive assumed-timing profile, 20 validation checks, key decisions, overlaps, and a searchable data dictionary. |
| **About** | Scope, sources, how they are combined, intended use and limitations, literature, and a suggested citation. |

### Navigating the tab

The tab has two parts:

* **Left: a vertical sub-menu** with one item per section (Overview, Timeline,
  Categories, Instruments, Policies, OECD scores, Methods, About). Click an item,
  or use the arrow keys, to show that section on the right. The selected item is
  highlighted and shows a short description of the section. Above the menu is a
  **quick search** (press <kbd>/</kbd> anywhere in the tab) across sections,
  sectors and all policy series. It can jump to a profile, a sector-filtered
  table, or a full-text search.
* **Right: the selected section**, shown full height, so drawers, tooltips and
  sticky panels behave as in the original. A top bar shows a breadcrumb (e.g.
  *Policy Timeline › Policies › Carbon Tax*), plus **Back / Forward / Reload**
  for pages visited in the tab and **New tab**, which opens the current view on
  its own. A page opened this way keeps the INPACT header (INPACT logo, title,
  subtitle and EPA logo, linked as on the main page) and the INPACT
  *Acknowledgements* and *Disclaimer* footer. The Policy Timeline's own section
  menu sits under the header. Header and footer come from
  `policies/templates/policies/_inpact_header.html`, `_inpact_footer.html` and
  `policies/static/policies/css/inpact-frame.css`, and are hidden inside the tab,
  where the main page already shows them.

On narrow screens (under 992 px wide) the sub-menu becomes a horizontal,
scrollable strip above the content.

**No CSV downloads inside the tab.** When the policy pages are shown in the
tab, every CSV download link is hidden: the footer link, the About page button,
*Download filtered CSV* on the Timeline and *Download these rows* on the
Policies table. They still appear on the standalone site at `/policy/`, and the
`/policy/download/dataset/` endpoint is unchanged.

Other features:
* **Shareable deep links:** the address bar follows the current page and its
  filters, e.g. `/#policy/timeline/?group=mechanism&year=2015` or
  `/#policy/policies/<slug>/`. Bookmark or share them.
* **Cross-links from the Explorer:** see [Explorer tab](#explorer-tab).

### How it works (for developers)

* `inpact_platform/urls.py` mounts `policies.urls` at `policy/`. All policy
  templates and scripts build URLs with `{% url %}` or `window.URLS`, so the
  prefix can be changed in one place.
* `policies/templates/policies/base.html` detects when it is framed by a page on
  the same origin. It then adds the `embedded` class (which hides the header and every
  element marked `csv-link`,
  see the end of `policies/static/policies/css/app.css`) and posts
  `{type: "policy-nav", kind: "load" | "state", path, title}` messages to the
  parent.
* `explorer/page/index.html`, section **9a. Policy Timeline tab**, handles those
  messages. It also contains the vertical sub-menu, search, history, deep-link
  (`#policy/...`) handling and frame sizing. The frame loads only when the tab
  is first opened, so the Explorer's start-up is not slowed down.

### Interpreting the policy data responsibly

* Intensity is a relative 0–1 index (implementation × coverage × bindingness).
  It is **not** tonnes of CO₂ avoided.
* Reported savings (kt CO₂e) were used only for selection. They repeat across
  years and sectors, so never sum them.
* Frameworks, portfolios and residual bundles overlap with other rows. Check
  each policy's aggregation role before adding series together.
* Years based on assumed timing are marked throughout.

---

## Trend Analysis tab

The former Streamlit "Piecewise Regression Dashboard", now a native page.

* `explorer/trend_engine.py`: piecewise OLS, Huber and Theil–Sen fits, the
  Mann–Kendall test, Sen's slope and prediction bands (numpy, scipy,
  statsmodels).
* `explorer/trend_views.py`: the JSON API (see the
  [URL and API reference](#url-and-api-reference)).
* The front-end uses Chart.js. It includes a segment-statistics table,
  Mann–Kendall and Sen's-slope KPIs, residual diagnostics, and CSV and PNG
  export.

It reads the same `data/sector_inventory/*.csv` files as the Explorer's Sector
Explorer, so both always show the same data.

---

## Structural Break Analysis tab

Explains the companion **Structural Break Analysis** app and links to it. That
app runs separately on Streamlit Community Cloud and opens in a new browser tab
(https://inpact-epa-structural-break-analysis.streamlit.app/). Nothing done
there changes this dashboard's data.

---

## About INPACT tab

Describes the project: mission, what it does, why it matters, data sources, the
team (photos in `explorer/static/img/team/`) and a closing statement. The text
follows the project's *About INPACT* document.

---

## Feedback tab

Submissions `POST` to `/api/feedback/` and are added as rows to an Excel
workbook, `data/feedback.xlsx`.

* **Local development:** leave `GITHUB_TOKEN` unset. The workbook is written to
  local disk.
* **Production (Vercel):** Vercel's filesystem is read-only, so the workbook is
  committed back to the GitHub repository through the GitHub Contents API. Create
  a fine-grained Personal Access Token with **Contents: Read and write** on the
  repo and set it as `GITHUB_TOKEN`.

The **Download .xlsx** button on the tab, or `/api/feedback/download/`, returns
the current workbook.

> ⚠️ Never commit your `GITHUB_TOKEN`. Keep it in environment variables only.

---

## Editing the data

| To change… | Edit | Then |
|---|---|---|
| National emissions (Explorer chart, KPIs) | `data/ghg_inventory.csv` | Reload the page |
| Sectoral emissions (Sector Explorer, Trend Analysis) | `data/sector_inventory/{Total,CO2,CH4,N2O}.csv` | Reload the page |
| Roadmap policies (Explorer markers, roadmap, intelligence panel) | `data/policies.csv` | Reload the page |
| Raster overlays | `data/Raster/*.tif` | Run `scripts/prerender_rasters.py` for Vercel |
| Policy Timeline dataset | files in `data/policy_timeline/` | Run `python manage.py load_policy_data` |
| Policy Timeline wording (instrument guide, milestones, literature, …) | `policies/editorial.py`, `policies/glossary.py` | Reload the page |

**`data/ghg_inventory.csv`** is in wide format. The first column is `year`, and
each other column is one gas in **kt CO₂-equivalent**. Headers must match the
page's indicator keys (`All greenhouse gases`, `CO2`, `CH4 - (CO2 equivalent)`,
…). A blank cell means no data, and the chart shows a gap. Add a row (e.g.
`2025`) to extend the timeline.

**`data/sector_inventory/*.csv`** has one file per gas. The first column is the
sector or subsector name and the other columns are years. All four files must
have the same year columns.

**`data/policies.csv`** has the columns `year, name, level, agency, sector, type,
instrument, description, direction, outcome`. `level` is `International`, `EU`,
`National` or `Target`. It sets the colour (navy, teal, emerald or amber) and
which sidebar checkbox controls the row. Target rows are always shown.

**Policy Timeline database.** The loader reads `data/policy_timeline/` (override
with `POLICY_DATA_DIR`) and rebuilds `policy_timeline.sqlite3`. It is safe to run
more than once, and it turns internal build notes into publication wording. The
release files themselves are kept unchanged for provenance.

```bash
python manage.py load_policy_data
python manage.py load_policy_data --data-dir /path/to/ireland_core_policy_release
```

---

## URL and API reference

**INPACT Explorer**

| Route | Purpose |
|---|---|
| `GET /` | The dashboard (all tabs) |
| `GET /api/rasters/` | Raster catalogue `{year:{sector:{parameter:file}}}` |
| `GET /api/raster/meta/?year=&sector=&parameter=` | Bounds, value range, colour stops, all-zero flag |
| `GET /api/raster/image/?year=&sector=&parameter=` | The rendered RGBA PNG overlay |
| `GET /api/trend/catalog/` | Gases, sectors and year axis for Trend Analysis |
| `GET /api/trend/series/?gas=&sector=` | Raw series |
| `POST /api/trend/fit/` | Fit, statistics and diagnostics |
| `POST /api/feedback/` | Record a feedback submission |
| `GET /api/feedback/download/` | Download the feedback workbook |

**Policy Timeline** (all under `/policy/`)

| Route | Deep link in the dashboard | Purpose |
|---|---|---|
| `/policy/` | `/#policy` | Overview |
| `/policy/timeline/` | `/#policy/timeline/` | Timeline |
| `/policy/categories/` | `/#policy/categories/` | Categories |
| `/policy/instruments/` | `/#policy/instruments/` | Instruments |
| `/policy/policies/` | `/#policy/policies/?sector=Transport` | Policies table |
| `/policy/policies/<slug>/` | `/#policy/policies/<slug>/` | Policy profile |
| `/policy/oecd-scores/` | `/#policy/oecd-scores/` | OECD scores |
| `/policy/method/` | `/#policy/method/` | Methods |
| `/policy/about/` | `/#policy/about/` | About and citation |
| `/policy/api/series/` | | All 47 series with attributes and 24-year arrays |
| `/policy/api/capmf/?level=3` | | CAPMF stringency series (levels 1–4) |
| `/policy/api/selection/` | | The 115 selection candidates and decisions |
| `/policy/api/year/<year>/` | | Snapshot of every series in one year (2000–2023) |
| `/policy/download/dataset/` | | Dataset CSV. Optional repeatable filters: `sector`, `layer`, `mechanism`, `policy_id`, `source`, `from`, `to` |

---

## Configuration (environment variables)

| Variable | Used by | Default |
|---|---|---|
| `SECRET_KEY` | Django (set a long random string in production) | dev-only key |
| `DEBUG` | Django (`1` to enable) | `0` |
| `GITHUB_TOKEN` | Feedback: commit the workbook to GitHub | unset (local disk) |
| `GITHUB_REPO` | Feedback: `owner/name` | `MehdiGalway/INPACT_V2` |
| `GITHUB_BRANCH` | Feedback: branch | `main` |
| `FEEDBACK_PATH` | Feedback: workbook path in the repo | `data/feedback.xlsx` |
| `POLICY_DATA_DIR` | Policy Timeline: release-files folder | `data/policy_timeline` |
| `SITE_PROJECT` | Policy Timeline: About page and citation | `INPACT` |
| `SITE_AUTHORS`, `SITE_INSTITUTION`, `SITE_CONTACT`, `SITE_URL` | Policy Timeline: attribution in the About page and citation | empty (set these before publishing) |
| `SITE_DATA_VERSION` | Policy Timeline: dataset version label | `25 September 2026` |

---

## Testing

```bash
python manage.py test policies explorer
```

* `policies` tests check the dataset's shape, the intensity formula, that every
  page and API responds, and that no internal build wording (file names, notes)
  appears in any public page, API response or download.
* `explorer` tests cover the Trend Analysis engine.

---

## Deployment

**Vercel.** Vercel detects `manage.py`, reads `WSGI_APPLICATION` and runs
`collectstatic`. No `vercel.json` is needed. Set `SECRET_KEY`, and optionally the
feedback and attribution variables above.

* The Policy Timeline's SQLite file is only read, never written, so it works on
  Vercel's read-only filesystem. Commit `data/policy_timeline/` together with the
  `.sqlite3` file.
* Raster overlays come from `data/RasterPrerendered/` there, because `rasterio`
  is not installed.
* **Bundle size:** `scipy` and `statsmodels` (Trend Analysis) and `pandas`
  (Policy Timeline export and Methods page) are large, and together they can
  exceed Vercel's serverless size limit. If they do, either host the site on a
  VM or a platform with full Python support (EC2, PythonAnywhere, Railway, …),
  or remove the Trend Analysis dependencies. Without them the Trend Analysis
  tab shows an API error, but the rest of the site works.

**Any WSGI host.** Run `python manage.py collectstatic`, then serve with, for
example, `gunicorn inpact_platform.wsgi`. WhiteNoise already serves the static
files, including the Policy Timeline's vendored Plotly and D3. Pages load fonts
and some libraries (Bootstrap, Leaflet, Chart.js) from CDNs, so the Explorer
needs an internet connection. The Policy Timeline's charts work offline.
