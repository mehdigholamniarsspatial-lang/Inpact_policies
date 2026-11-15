"""Recorded source checks, independent of historical input-file retrieval dates.

Dates are evidence from a completed review, never the current request date.
"""
import json
import re
from pathlib import Path

CHECKS = json.loads((Path(__file__).with_name('source_link_checks.json')).read_text(encoding='utf-8'))


def resolve_url(url):
    return CHECKS.get(url, {}).get('url', url)


def source_check(url):
    return CHECKS.get(url, {})


def refresh_citation(text):
    urls = re.findall(r'https?://[^\s]+', text)
    checks = []
    for token in urls:
        url = token.rstrip('.,;)')
        check = source_check(url)
        if check:
            text = text.replace(url, check['url'])
            checks.append(check)
    if not checks:
        return text
    # Remove old retrieval annotations, including prior rendered review notes.
    text = re.sub(r'\s*\((?:accessed|checked) [^)]*\)', '', text)
    text = re.sub(r'\s*\[Source check: [^\]]*\]', '', text)
    verified = all(c['verified'] for c in checks)
    label = 'accessed' if verified else 'checked'
    text = text.rstrip() + f' ({label} 15 November 2026)'
    notes = list(dict.fromkeys(c['note'] for c in checks if c.get('note')))
    if notes:
        text += ' [Source check: ' + ' '.join(notes) + ']'
    return text
