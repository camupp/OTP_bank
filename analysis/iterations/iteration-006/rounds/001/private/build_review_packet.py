"""Build a neutral reviewer view. Exact originals and alias mapping stay outside it.
Run only after concepts and independent checks are complete. No source edits.
"""
from pathlib import Path
import json
import re
import hashlib
import shutil
import csv
import io

R = Path(__file__).resolve().parent.parent
P = R / 'review-packet'
ALIASES = {
    'V01': ('CON-017@v1', 'candidate', 'branches/B/concept-017.md', 'branches/B'),
    'V02': ('CON-015@v1', 'incumbent', '../../incumbent/concept.md', '../../incumbent'),
    'V03': ('BASELINE', 'baseline', 'inputs/baseline.md', None),
    'V04': ('CON-016@v2', 'candidate', 'branches/A/concept-016.md', 'branches/A'),
}
KEY_TO_ALIAS = {v[0]: k for k, v in ALIASES.items()}

def neutral(text):
    for key, alias in KEY_TO_ALIAS.items():
        text = text.replace(key, alias)
    text = re.sub(r'CON-\d+@v\d+', 'сопоставляемый вариант', text)
    text = re.sub(r'CON-\d+', 'сопоставляемый вариант', text)
    text = re.sub(r'iteration-\d+', 'исследовательский пакет', text)
    text = re.sub(r'branches/[AB]/', 'specifications/', text)
    text = re.sub(r'incumbent|прежний лучший|предыдущий победитель', 'вариант', text, flags=re.I)
    # File locations that reveal run lineage are not assigned reviewer inputs.
    text = re.sub(r'analysis/iterations/[^\s`"<>),;]+', 'shared/источник', text)
    text = text.replace('inputs/', 'shared/')
    text = text.replace('supporting/reward-', 'shared/reward-')
    text = text.replace('supporting/employee-profiles.md', 'shared/employee-profiles.md')
    text = text.replace('supporting/finance-basis/basis.md', 'shared/finance-basis.md')
    text = text.replace('supporting/finance-basis/scenario-inputs.json', 'shared/finance-basis.json')
    text = re.sub(r'finance-spec-\d+\.json', 'finance-spec.json', text)
    text = re.sub(r'assumptions-\d+\.csv', 'assumptions.csv', text)
    text = text.replace('A / B / C', 'V04 / V01 / V02')
    text = text.replace('V044,404', 'V04 — 4,404')
    return text

def clean_json(value):
    if isinstance(value, dict):
        return {neutral(k): clean_json(v) for k, v in value.items()
                if k not in {'parents', 'parent_candidates', 'lineage', 'origin_path',
                             'prior_candidate_key', 'prior_best', 'provenance_files',
                             'previous_winner', 'author', 'branch_id'}}
    if isinstance(value, list):
        return [clean_json(v) for v in value]
    return neutral(value) if isinstance(value, str) else value

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding='utf-8')

def jwrite(path, value):
    write(path, json.dumps(value, ensure_ascii=False, indent=2) + '\n')

def candidate_view(text, alias):
    # Remove explicit ancestry paragraphs, retaining the actual mechanism and tests.
    paragraphs = text.split('\n\n')
    kept = []
    for paragraph in paragraphs:
        if re.search(r'lineage|авторств|истори[яю] побед|родител|прежн.{0,12}побед|изменения относительно|отличия от', paragraph, re.I):
            if paragraph.lstrip().startswith('- '):
                lines = [line for line in paragraph.splitlines()
                         if not re.search(r'lineage|родител|Происхождение механики|истори[яю] побед', line, re.I)]
                if lines:
                    kept.append('\n'.join(lines))
                continue
            if 'Отвергнуть' in paragraph:
                kept.append(paragraph[paragraph.index('Отвергнуть'):])
            continue
        if paragraph.startswith('Вместо четырёх нижних'):
            continue
        kept.append(paragraph)
    return '# ' + alias + '\n\n' + neutral('\n\n'.join(kept))

def main():
    (P / 'shared').mkdir(parents=True, exist_ok=True)
    mapping = {'aliases': {a: {'candidate_key': v[0], 'kind': v[1], 'origin_path': v[2]}
                           for a, v in ALIASES.items()}}
    jwrite(R / 'private/review-map.json', mapping)
    for alias, (key, kind, origin, specdir) in ALIASES.items():
        source = (R / origin).read_text()
        if kind == 'baseline':
            source = source.split('## Общая финансовая основа M05')[0].split('## Общая M05')[0]
        write(P / 'candidates' / (alias + '.md'), candidate_view(source, alias))
        if specdir:
            src = (R / specdir).resolve()
            for name in ['finance-spec.json', 'employee-profiles.csv', 'assumptions.csv',
                         'self-check.json', 'employee-card.md', 'first-launch.json']:
                f = src / name
                if f.exists():
                    if f.suffix == '.json':
                        jwrite(P / 'specifications' / alias / name, clean_json(json.loads(f.read_text())))
                    else:
                        write(P / 'specifications' / alias / name, neutral(f.read_text()))
    # Shared documents are presentation views; the rubric itself is unchanged.
    shutil.copyfile(R / 'inputs/rubric.json', P / 'shared/rubric.json')
    write(P / 'shared/assignment.md', (R / 'private/review-assignment-draft.md').read_text())
    write(P / 'shared/context.md', (R / 'private/review-assignment-draft.md').read_text())
    write(P / 'shared/baseline.md', neutral((R / 'inputs/baseline.md').read_text()))
    write(P / 'shared/finance-basis.md', neutral((R / 'supporting/finance-basis/basis.md').read_text()))
    for name in ['reward-basis.md', 'employee-profiles.md']:
        write(P / 'shared' / name, neutral((R / 'supporting' / name).read_text()))
    write(P / 'shared/diagnosis.md', neutral((R / 'inputs/diagnosis.md').read_text()))
    write(P / 'shared/evidence.md', neutral((R / 'inputs/evidence.md').read_text()))
    jwrite(P / 'shared/finance-basis.json', clean_json(json.loads((R / 'supporting/finance-basis/scenario-inputs.json').read_text())))
    jwrite(P / 'shared/reward-sources.json', clean_json(json.loads((R / 'supporting/reward-sources.json').read_text())))
    checks = {}
    for name in ['finance', 'evidence']:
        preferred = R / 'checks' / name / (name + '-for-review.json')
        if not preferred.exists():
            preferred = R / 'checks' / (name + '.json')
        checks[name] = clean_json(json.loads(preferred.read_text()))
        for ext in ['md']:
            f = R / 'checks' / name / (name + '-for-review.' + ext)
            if not f.exists():
                f = R / 'checks' / (name + '-for-review.' + ext)
            if not f.exists():
                f = R / 'checks' / (name + '.' + ext)
            if f.exists():
                write(P / 'checks' / (name + '.' + ext), neutral(f.read_text()))
        folder = R / 'checks' / name
        if folder.exists():
            for f in folder.rglob('*'):
                if not f.is_file() or f.suffix not in {'.csv', '.json'}:
                    continue
                rel = f.relative_to(folder)
                if any(x in str(rel) for x in ['initial', 'before-', 'retry-burst', 'source-manifest', 'delta']):
                    continue
                if name == 'evidence' and f.name != 'evidence-for-review.json':
                    continue
                target = P / 'calculations' / name / neutral(str(rel))
                if f.suffix == '.json':
                    jwrite(target, clean_json(json.loads(f.read_text())))
                else:
                    rows = list(csv.DictReader(io.StringIO(f.read_text())))
                    if rows:
                        rows = [row for row in rows if row.get('candidate_key') != 'CON-016@v1']
                        out = io.StringIO()
                        writer = csv.DictWriter(out, fieldnames=rows[0].keys() if rows else [])
                        if rows:
                            writer.writeheader(); writer.writerows(rows)
                        write(target, neutral(out.getvalue()))
    for name, payload in checks.items():
        paths = sorted(str(f.relative_to(P)) for f in (P / 'calculations' / name).rglob('*') if f.is_file())
        for result in payload.get('results', []):
            if 'calculation_paths' in result:
                result['calculation_paths'] = paths
    jwrite(P / 'checks.json', checks)
    write(P / 'README.md', '# Независимая оценка\n\nЧитайте shared/assignment.md, shared/rubric.json, candidates/V01…V04.md, checks.json и приложенные проверки. Происхождение вариантов, приватная карта и документы вне этого пакета не назначены к чтению. Все ссылки на факты ОТП раскрыты в shared/evidence.md и shared/reward-sources.json.\n')
    files = {str(f.relative_to(P)): hashlib.sha256(f.read_bytes()).hexdigest()
             for f in P.rglob('*') if f.is_file() and f.name != 'manifest.json'}
    jwrite(P / 'manifest.json', {'files': files, 'view_policy': 'Neutral presentation copies; exact source versions retained privately. No score history or authors assigned.'})

if __name__ == '__main__':
    main()
