"""Inventory and HTTP-check the external sources rendered by the Policy Timeline."""
import concurrent.futures
import csv
import html
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from policies import editorial
import requests

def inventory():
    sources = {}
    def add(url, context):
        sources.setdefault(html.unescape(url).rstrip('.,;)'), set()).add(context)
    with sqlite3.connect(ROOT / 'data/policy_timeline/policy_timeline.sqlite3') as db:
        for slug, citation, reference in db.execute('select slug, source_citation, reference_url from policies_policyseries'):
            for text in (citation, reference):
                for url in re.findall(r'https?://[^\s;]+', text):
                    add(url, slug + ': ' + text)
    with (ROOT / 'data/policy_timeline/config/references.csv').open(encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            add(row['url'], row['title'])
    for pub, title, year, url in editorial.VERIFICATION_SOURCES:
        add(url, title)
    return sources

def check(item):
    url, contexts = item
    result = dict(url=url, contexts=sorted(contexts), checked_on='2026-11-15')
    try:
        response = requests.get(url, timeout=35, headers={'User-Agent': 'Mozilla/5.0 (compatible; source-link-verification)'})
        result.update(http_status=response.status_code, final_url=response.url, content_type=response.headers.get('Content-Type', ''))
        if 'pdf' in result['content_type']:
            try:
                import io
                from pypdf import PdfReader
                doc = PdfReader(io.BytesIO(response.content))
                text = '\n'.join(p.extract_text() or '' for p in doc.pages)
            except Exception:
                text = 'PDF received; text extraction unavailable'
        else:
            text = re.sub(r'<(script|style)\b[^>]*>.*?</\1>', '', response.text, flags=re.S | re.I)
            title = re.search(r'<title[^>]*>(.*?)</title>', text, re.S | re.I)
            result['title'] = html.unescape(title.group(1).strip()) if title else ''
            text = html.unescape(re.sub('<[^>]+>', ' ', text))
        result['text'] = re.sub(r'\s+', ' ', text)[:60000]
    except Exception as exc:
        result['error'] = str(exc)
    return result

if __name__ == '__main__':
    sources = inventory()
    target = ROOT / 'audit/source_link_http_checks.json'
    previous = json.loads(target.read_text(encoding='utf-8')) if target.exists() else []
    if '--pdf-only' in sys.argv:
        sources = {r['url']: r['contexts'] for r in previous if 'pdf' in r.get('content_type', '')}
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(check, sources.items()))
    if '--pdf-only' in sys.argv:
        updates = {r['url']: r for r in results}
        results = [updates.get(r['url'], r) for r in previous]
    target.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    for i, row in enumerate(results):
        print(i, row.get('http_status', 'ERROR'), row['url'], row.get('title', ''), row.get('error', '')[:100])
    print('TOTAL', len(results))
