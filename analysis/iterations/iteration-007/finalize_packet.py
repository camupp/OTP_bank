"""Pre-review presentation fixes only; never modify a reviewed or sealed packet."""
from pathlib import Path
import hashlib
import json
import re
import sys

run = Path(__file__).resolve().parent
rd = run / 'rounds' / f'{int(sys.argv[1]):03d}'
assert not (rd / 'snapshot.json').exists() and not (rd / 'review.json').exists()
packet = rd / 'review-packet'
changes = []
mapping = json.loads((rd / 'private/review-map.json').read_text())['aliases']
ids = {re.search(r'CON-(\d+)', r['candidate_key']).group(1): alias
       for alias, r in mapping.items() if r['candidate_key'].startswith('CON-')}

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

for name in ['limits.json', 'universal-tiers.csv', 'finance.json', 'verification.json',
             'independent-verification.json']:
    source = rd / 'supporting/finance-basis' / name
    target = packet / 'shared/finance-basis' / name
    if source.exists() and not target.exists():
        target.write_bytes(source.read_bytes())
        changes.append({'file': str(target.relative_to(packet)), 'action': 'add common non-code financial basis'})

for path in packet.rglob('*'):
    if not path.is_file() or path.name == 'manifest.json':
        continue
    relative = str(path.relative_to(packet))
    if relative.startswith(('shared/fixtures/source/', 'shared/fixtures/patches/')):
        continue
    if relative.startswith('specifications/') and path.name == 'README.md':
        changes.append({'file': relative, 'before_sha256': digest(path), 'action': 'omit author file-navigation metadata'})
        path.unlink()
        continue
    before = path.read_text()
    content = before.replace('CON016_DESIGN', 'MEASUREMENT_DESIGN')
    content = re.sub(r'CON-?(\d{3})/(\d{3})',
                     lambda m: ids.get(m.group(1), 'сценарий') + '/' + ids.get(m.group(2), 'сценарий'),
                     content, flags=re.I)
    content = re.sub(r'CON-?(\d{3})', lambda m: ids.get(m.group(1), 'описанного сценария'),
                     content, flags=re.I)
    content = re.sub(r'\bA1[89]-prospective-\d+\b', 'current-rule', content)
    content = content.replace('Подробный diff/lineage только в changes.md и branch.json.', '')
    content = content.replace('parent48 award approvals', 'conservative48 award approvals')
    content = content.replace('retain original parent quote only as provenance', 'retain the original quotation as a separate disclosed assumption')
    if path.suffix == '.md':
        def link(match):
            label, target = match.group(1), match.group(2).strip('<>')
            local = target.split('#')[0]
            if not local or local.startswith(('http://', 'https://')) or (path.parent / local).exists():
                return match.group(0)
            if relative == 'shared/source-evidence-brief.md' and local == 'claims.json':
                return '[' + label + '](source-claims.json)'
            if local.endswith('.py') or Path(local).name == 'source-manifest.json':
                return label + ' — технический исходник или аудит происхождения сохранён у координатора'
            if relative.startswith('shared/round002-stress/') and ('common-checks' in local or 'coordinator-only/' in local):
                return label + ' — подготовительный технический контракт или проверка; полная версия сохранена у координатора'
            raise ValueError('Unresolved packet link: ' + relative + ' -> ' + target)
        content = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', link, content)
    if content != before:
        old = digest(path)
        path.write_text(content)
        changes.append({'file': relative, 'before_sha256': old, 'after_sha256': digest(path),
                        'action': 'repair navigation or remove technical identity metadata; preserve rules and quantities'})

files = {str(p.relative_to(packet)): digest(p) for p in packet.rglob('*')
         if p.is_file() and p != packet / 'manifest.json'}
(packet / 'manifest.json').write_text(json.dumps({'files': files}, ensure_ascii=False, indent=2) + '\n')
log_path = rd / 'private/packet-presentation-corrections.json'
prior_changes = json.loads(log_path.read_text())['changes'] if log_path.exists() else []
log_path.write_text(json.dumps({'pre_review_only': True, 'changes': prior_changes + changes},
                               ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'files': len(files), 'presentation_corrections': len(changes)}, ensure_ascii=False))
