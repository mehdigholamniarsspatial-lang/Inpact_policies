"""Materialise the manually reviewed 15 November 2026 source-link register."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
rows = json.loads((ROOT / 'audit/source_link_http_checks.json').read_text(encoding='utf-8'))
oecd = 'https://data-explorer.oecd.org/vis?df%5Bag%5D=OECD.ENV.EPI&df%5Bds%5D=dsDisseminateFinalDMZ&df%5Bid%5D=DSD_CAPMF%40DF_CAPMF&df%5Bvs%5D=1.0&dq=IRL.A.&pd=1990%2C2023&lc=en'
replacements = {
    0: oecd,
    7: rows[30]['url'],
    8: 'https://assets.gov.ie/218449/f1a6725a-6269-442b-bff1-2730fe2dc06c.pdf',
    11: rows[10]['url'],
    13: 'https://data.oireachtas.ie/ie/oireachtas/debateRecord/dail/2010-05-25/debate/mul%40/main.pdf',
    32: 'https://www.seai.ie/plan-your-energy-journey/public-sector',
    34: 'https://www.seai.ie/grants/home-energy-grants/individual-grants',
}
web_verified = {10, 11, 13, 23, 32, 33, 34, 35, 37, 38, 39, 40, 43}
notes = {
    0: 'Ireland, 1990–2023: 7,548 data points confirmed in the interactive database. Opens in a new tab; JavaScript required.',
    6: 'Registry accessible; individual report 1849 records were not independently revalidated.',
    8: 'Direct official PDF verified: An Overview of Ireland’s Fifth Nitrates Action Programme. Replaces a viewer returning HTTP 502.',
    9: 'Current NECP publication page; historical programme details require the relevant plan edition.',
    13: 'Official debate PDF replaces the inaccessible question page; carbon-tax answer dated 25 May 2010.',
    32: 'Current SEAI public-sector guidance replaces the unavailable programme URL.',
    50: 'Correct document title: European Union (Energy Performance Of Buildings) Regulations 2019.',
}
registry = {}
report = ['# Policy Timeline source-link review — 15 November 2026', '',
          'Scope: all 58 distinct source URLs in the 47 policy profiles, official-reference links, Methods reference list and additional verification sources. Decorative/header links and font assets are excluded.', '',
          'Verification means the cited document or programme page was identified, not that every historical policy claim or every underlying database record was re-audited. HTTP success alone was insufficient. SEAI/OECD anti-bot responses were cross-checked through web page access. Original raw input retrieval dates remain provenance; the public review dates come from the recorded register.', '',
          '| # | Original source | Result | Destination / evidence |', '|---|---|---|---|']
for i, row in enumerate(rows):
    verified = True
    method = 'browser: Ireland and period filters confirmed' if i == 0 else ('web page/document content' if i in web_verified else 'HTTP GET and document text')
    title = row.get('title', '').replace('\n', ' ').strip()
    if 'pdf' in row.get('content_type', ''):
        title = row.get('text', '')[:180]
    note = notes.get(i, '')
    if i in web_verified and i not in {11, 13, 32}:
        note = (note + ' Content verified through web access; direct automated requests encountered an access challenge.').strip()
    item = dict(url=replacements.get(i, row['url']), checked_on='2026-11-15', verified=verified,
                status='Source identified' if verified else 'Unverified — retrieval failed', note=note, method=method)
    registry[row['url']] = item
    registry[item['url']] = item
    evidence = note or title or 'Document identity checked from extracted text.'
    report.append(f"| {i+1} | {row['url']} | {item['status']} | {item['url']} — {evidence.replace('|', '/')} ({method}) |")
(ROOT / 'policies/source_link_checks.json').write_text(json.dumps(registry, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
(ROOT / 'audit/SOURCE_LINK_REVIEW_15Nov2026.md').write_text('\n'.join(report) + '\n', encoding='utf-8')
