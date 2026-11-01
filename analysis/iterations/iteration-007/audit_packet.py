"""Read-only packet/source audit; writes only a private report in an unsealed round."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import re
import sys

run = Path(__file__).resolve().parent
rd = run / 'rounds' / f'{int(sys.argv[1]):03d}'
if (rd / 'snapshot.json').exists():
    raise SystemExit('Sealed round: no report mutation allowed')
packet = rd / 'review-packet'
mapping = json.loads((rd / 'private/review-map.json').read_text())['aliases']
manifest = json.loads((packet / 'manifest.json').read_text())['files']
pins = json.loads((rd / 'private/versions-before-checks.json').read_text())
pins = pins.get('files', pins)
version_changes = [p for p, h in pins.items()
                   if hashlib.sha256((rd / p).read_bytes()).hexdigest() != h]

def quantities(text):
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text = re.sub(r'`[^`]+`', '', text)
    # Check money, time, rates and proportions, excluding filenames and IDs.
    return Counter(re.findall(r'\d+(?:[.,]\d+)?\s*(?:млн|тыс|RUB|R|C|%|час|ч\b|мин|дней|дня|квартал)', text))

quant_checks = []
for alias, record in mapping.items():
    original = quantities((rd / record['origin_path']).read_text())
    anonymized = quantities((packet / 'candidates' / f'{alias}.md').read_text())
    quant_checks.append({'alias': alias, 'money_hour_percent_tokens_unchanged': original == anonymized,
                         'missing_tokens': list((original - anonymized).elements()),
                         'extra_tokens': list((anonymized - original).elements())})
broken = []
for p in packet.rglob('*.md'):
    for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)', p.read_text()):
        target = target.strip('<>').split('#')[0]
        if not target or target.startswith(('https://', 'http://')):
            continue
        if not (p.parent / target).exists():
            broken.append({'file': str(p.relative_to(packet)), 'target': target})
source_checks = []
for family, members in [('fixtures', ['source', 'patches']),
                        ('round002-stress', ['source', 'patches', 'business-config.json', 'reader.py'])]:
    origin = rd / 'supporting' / family
    for member in members:
        source = origin / member
        paths = source.rglob('*') if source.is_dir() else [source]
        for p in paths:
            if not p.is_file() or '__pycache__' in p.parts:
                continue
            target = packet / 'shared' / family / p.relative_to(origin)
            source_checks.append({'path': str(target.relative_to(packet)),
                                  'identical_bytes': target.is_file() and target.read_bytes() == p.read_bytes()})
report = {
    'candidate_versions_unchanged': not version_changes,
    'changed_version_files': version_changes,
    'quantitative_text_checks': quant_checks,
    'packet_hashes_match': all(hashlib.sha256((packet / p).read_bytes()).hexdigest() == h
                               for p, h in manifest.items()),
    'broken_local_links': broken,
    'source_bytes_checked': len(source_checks),
    'source_byte_mismatches': [x['path'] for x in source_checks if not x['identical_bytes']],
    'scope': 'Identity/quantitative fidelity and links; no claim of substantive financial correctness.'
}
(rd / 'private/packet-fidelity-audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(report, ensure_ascii=False, indent=2))
