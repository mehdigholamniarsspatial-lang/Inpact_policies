"""Record the approved overview wording changes against the pre-correction commit."""
from pathlib import Path
import difflib
import re
import subprocess
from docx import Document
from docx.shared import Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[2]
FILES = ['policies/templates/policies/overview.html', 'policies/static/policies/js/overview.js']
doc = Document()
sec = doc.sections[0]
sec.top_margin = sec.bottom_margin = Inches(.7)
style = doc.styles['Normal']
style.font.name = 'Calibri'
style.font.size = Pt(10)
style.paragraph_format.space_after = Pt(6)
doc.add_heading('Policy overview: correction report', 0)
doc.add_paragraph('31 October 2026 | /policy/ | Cross-cutting editorial corrections')
doc.add_paragraph('The overview now distinguishes recorded policy activity from legal commencement, explains the intensity index as a proxy, and clarifies selection, sector comparisons and residual bundles. Policy dates, scores, source extracts and selection rules are unchanged.')
doc.add_heading('Verification', 1)
doc.add_paragraph('Data reload completed: 47 series and 1,128 annual records. Django system check: no issues. Django policy tests: 7 passed, 0 failures. The corrected overview and source chart were checked in a browser using a fresh local preview. JavaScript syntax check passed. The test environment reports a missing collected-static directory; source assets are available through the development server.')
doc.add_heading('Evidence', 1)
sources = [
('E1', 'OECD CAPMF explainer, framework scope and interpretation, sections 1–3', 'https://www.oecd.org/en/data/insights/data-explainers/2025/04/the-climate-actions-and-policies-measurement-framework-capmf.html'),
('E2', 'EPA final greenhouse-gas inventory 1990–2024, Table 4, 2023 sector emissions', 'https://www.epa.ie/publications/monitoring--assessment/climate-change/air-emissions/EPA-Final-GHG-Emissions-Report-1990-2024.pdf'),
('E3', 'Release selection, timing and residual membership evidence', 'data/policy_timeline/sector_materiality.csv; selection_log.csv; ireland_core_policy_timeline.csv; qa/residual_members.csv; config/timing_parameters.csv'),
('E4', 'Chart counting and hatching implementation', 'policies/static/policies/js/overview.js; policies/static/policies/js/timeline.js'),
]
for key,title,url in sources:
    doc.add_paragraph(f'{key}. {title}. Accessed / inspected 31 October 2026.\n{url}')

def clean(s):
    s = re.sub(r'<[^>]+>', '', s.strip())
    return s

n = 0
for file in FILES:
    old = subprocess.check_output(['git','show',f'HEAD:{file}'], cwd=ROOT).decode('utf-8').splitlines()
    new = (ROOT/file).read_text(encoding='utf-8').splitlines()
    for tag,a,b,c,d in difflib.SequenceMatcher(None,old,new).get_opcodes():
        if tag == 'equal': continue
        before,after = '\n'.join(old[a:b]),'\n'.join(new[c:d])
        if '/*' in after: continue
        n += 1
        doc.add_heading(f'{n}. Overview wording', 1)
        doc.add_paragraph(f'Policy ID / name: ALL (cross-cutting); selected policy overview.\nLocation: /policy/ — {file}, line {c+1}.')
        for label, value in [('Original', clean(before) or '(No overview-specific subtitle.)'), ('Corrected', clean(after))]:
            p=doc.add_paragraph()
            p.add_run(label+': ').bold=True
            p.add_run(value)
        evidence='E1, E3 and E4'
        reason='Clarifies that the displayed record and indices follow dataset conventions and do not establish legal commencement, observed implementation or emissions reductions.'
        if any(x in after for x in ['90%', '2024–2030']):
            reason='States the selection denominator and retrospective bias accurately, including the zero-denominator LULUCF exception and projected savings.'
            evidence='E3; audit findings F11 and selection verification'
        elif any(x in after for x in ['Agriculture', 'Emissions context', 'Differences in series']):
            reason='Anchors the emissions comparison to 2023 and limits policy-count and OECD-coverage claims to the selected dataset.'
            evidence='E1, E2 and E3'
        elif any(x in after for x in ['Rows are not additive', 'bundle scores', 'Members are documented']):
            reason='Distinguishes overlap from residual membership: residual members are not separate core rows and bundle scores are averages.'
            evidence='E3; audit finding F10'
        elif 'hatch' in after:
            reason='Describes the implemented hatching rule, including the unhatched residual-bundle exception.'
            evidence='E3 and E4; audit finding F15'
        elif 'Core series from recorded start' in after or 'Sources of the implementation proxy' in after:
            reason='Matches the existing chart population, which excludes residuals and includes post-expiry years.'
            evidence='E4; audit finding F13'
        doc.add_paragraph(f'Reason: {reason}\nEvidence: {evidence}. Accessed / inspected 31 October 2026; exact URLs and local locators are listed above.')
doc.save(ROOT/'audit/POLICY_CORRECTION_REPORT.docx')
print(f'Wrote correction report with {n} change records.')
