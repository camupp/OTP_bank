"""Coordinator-only copy of completed checks into the blinded review packet."""
import json
import re
from pathlib import Path

r = Path(__file__).resolve().parents[1]
aliases = json.loads((r / 'private/review-map.json').read_text())['aliases']
keys = {v['candidate_key']: a for a, v in aliases.items()}
assumptions = json.loads((r / 'private/assumption-map.json').read_text())
paths = {v['origin_path']: f'review-packet/candidates/{a}.md' for a, v in aliases.items() if v['kind'] == 'candidate'}
paths.update({
    'branches/A/assumptions.csv': 'review-packet/assumptions.md',
    'branches/B/assumptions.csv': 'review-packet/assumptions.md',
    'branches/B/economics.md': 'review-packet/economic-notes.md',
    'checks/finance': 'review-packet/finance',
    'checks/evidence': 'review-packet/evidence',
})

def clean(s):
    for old, new in sorted(paths.items(), key=lambda p: -len(p[0])):
        s = s.replace(old, new)
    for old, new in sorted(keys.items(), key=lambda p: -len(p[0])):
        s = s.replace(old, new)
    for old, new in keys.items():
        if '@' in old:
            s = s.replace(old.split('@')[0], new)
    for old, new in sorted(assumptions.items(), key=lambda p: -len(p[0])):
        s = s.replace(old, new)
    for n in range(1, 5):
        s = s.replace(f'concept-{n:03}.md', f'review-packet/candidates/{keys[f"CON-{n:03}@v1"]}.md')
    s = s.replace('candidate_key', 'alias')
    s = s.replace('branch_B_normalized_quarter', 'normalized_quarter')
    s = s.replace('branch_B_fixture', 'normalized_fixture')
    s = s.replace('Квартальный пример B', 'Квартальный условный пример')
    s = s.replace('A использует g как множитель цен, B — π как темп роста', 'В документах g обозначает множитель цены, π — темп роста')
    s = s.replace('У обеих A-концепций', f'У {keys["CON-001@v1"]} и {keys["CON-002@v1"]}')
    s = s.replace('у B это условие', 'в экономическом приложении это условие')
    s = s.replace('концепции A,', f'{keys["CON-001@v1"]}/{keys["CON-002@v1"]},')
    s = s.replace('концепции B,', f'{keys["CON-003@v1"]}/{keys["CON-004@v1"]},')
    s = s.replace('`inputs/`, `branches/`, `checks/`', '`inputs/`, `review-packet/`')
    s = s.replace('исходный branch', 'исходный документ')
    s = s.replace('A, строки 53 обеих концепций', f'{keys["CON-001@v1"]}/{keys["CON-002@v1"]}, строки 53')
    s = s.replace('B/economics.md', 'review-packet/economic-notes.md')
    s = s.replace('В A g —', f'В {keys["CON-001@v1"]}/{keys["CON-002@v1"]} g —')
    s = s.replace('в B π —', 'в экономическом приложении π —')
    return s

for group in ('finance', 'evidence'):
    out = r / 'review-packet' / group
    out.mkdir(exist_ok=True)
    for source in sorted((r / 'checks' / group).iterdir()):
        if source.name == 'verify_artifacts.py':
            continue  # Administrative provenance audit exposes branch identities.
        if source.is_file() and source.suffix in ('.md', '.csv', '.json', '.py'):
            (out / source.name).write_text(clean(source.read_text()))
    (r / f'review-packet/{group}.json').write_text(clean((r / f'checks/{group}.json').read_text()))

finance = json.loads((r / 'checks/finance.json').read_text())
evidence = json.loads((r / 'checks/evidence.json').read_text())
fi = {x['candidate_key']: x for x in finance['results']}
ev = {x['candidate_key']: x for x in evidence['results']}
results = []
for alias, record in aliases.items():
    key = record['candidate_key']
    f = {k: v for k, v in fi[key].items() if k != 'candidate_key'}
    e = {k: v for k, v in ev[key].items() if k != 'candidate_key'}
    results.append({'alias': alias, 'kind': record['kind'], 'finance': f, 'evidence': e})
packet = {'schema_version': 1, 'path_base': 'round directory; knowledge/ and analysis/preparation/ relative to project root',
          'interpretation': 'Evidence support covers listed claims only. Synthetic calculations are not measured bank costs or effects.',
          'results': results}
(r / 'review-packet/checks.json').write_text(clean(json.dumps(packet, ensure_ascii=False, indent=2)) + '\n')
admin_copy = r / 'review-packet/finance/verify_artifacts.py'
if admin_copy.exists():
    admin_copy.unlink()

def remove_admin_refs(value):
    if isinstance(value, list):
        return [remove_admin_refs(x) for x in value if not (isinstance(x, str) and x.endswith('/verify_artifacts.py'))]
    if isinstance(value, dict):
        return {k: remove_admin_refs(v) for k, v in value.items()}
    return value

for path in (r / 'review-packet').rglob('*.json'):
    data = remove_admin_refs(json.loads(path.read_text()))
    if path.name == 'artifact-validation.json':
        data.pop('source_sha256', None)
        data.pop('result_sha256', None)
        data['blinding_note'] = 'Administrative provenance hashes omitted; original verification record retained outside reviewer inputs.'
    if path.parent.name == 'finance' and path.name == 'validation.json':
        for field in ('input_sha256', 'script_sha256'):
            if field in data:
                data['original_execution_' + field] = data.pop(field)
        data['blinding_note'] = 'Execution hashes refer to original calculation files before identifier substitution, not to these review copies.'
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'copied_checks': len(results), 'support_files': sum(1 for p in (r/'review-packet').rglob('*') if p.is_file())}))
