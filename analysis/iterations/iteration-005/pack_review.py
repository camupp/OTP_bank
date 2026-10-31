"""Coordinator packaging only. Never run on a sealed round."""
from pathlib import Path
import json
import csv
import hashlib
import random
import re
import sys
import io

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[2]
number = int(sys.argv[1])
rd = RUN / 'rounds' / f'{number:03d}'
if (rd / 'snapshot.json').exists():
    raise SystemExit('Sealed round: no mutation allowed')
packet = rd / 'review-packet'
if packet.exists() and any(p.is_file() for p in packet.rglob('*')):
    raise SystemExit('Packet exists: audit before any explicit correction')
packet.mkdir(exist_ok=True)
for folder in ['candidates', 'shared', 'specifications', 'calculations']:
    (packet / folder).mkdir(exist_ok=True)

def read(p):
    return json.loads(p.read_text())

def save(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

records = [{'candidate_key': 'BASELINE', 'kind': 'baseline', 'origin_path': 'inputs/baseline.md'}]
for branch in ['A', 'B']:
    data = read(rd / 'branches' / branch / 'branch.json')
    for c in data['candidates']:
        records.append({'candidate_key': c['candidate_key'], 'kind': 'candidate', 'origin_path': c['path']})
prior = read(rd / 'round.json')['prior_best']
if prior:
    source = RUN / prior['artifact_path']
    records.append({'candidate_key': prior['candidate_key'], 'kind': 'incumbent', 'origin_path': str(source.relative_to(rd)) if source.is_relative_to(rd) else str(Path(__import__('os').path.relpath(source, rd)))})
random.Random(500 + number).shuffle(records)
aliases = {f'V{i + 1:02d}': r for i, r in enumerate(records)}
keymap = {r['candidate_key']: a for a, r in aliases.items()}
save(rd / 'private/review-map.json', {'aliases': aliases})
group_labels = {b: '/'.join(a for a, r in aliases.items() if r['kind'] == 'candidate' and r['origin_path'].startswith('branches/' + b + '/')) for b in ['A', 'B']}

def neutral(text, redact_group_labels=False):
    for key in sorted(keymap, key=len, reverse=True):
        text = text.replace(key, keymap[key])
        text = text.replace(key.replace('-', '').replace('@', ''), keymap[key])
    text = re.sub(r'CON-\d+(?:@v\d+|-v\d+)', 'variant', text)
    text = re.sub(r'incumbent', 'reference', text, flags=re.I)
    text = re.sub(r'branches/[AB]', 'specifications', text)
    text = text.replace('v1_total_hours_month', 'declared_primary_qa_hours_month')
    text = re.sub(r'\bv[1-9]\d*\b', 'редакция', text)
    text = re.sub(r'finance-spec-\d+\.json', 'finance-spec.json', text)
    text = re.sub(r'assumptions-\d+\.csv', 'assumptions.csv', text)
    text = text.replace('supporting/synthetic-examples.', 'shared/synthetic-examples.')
    for a, r in aliases.items():
        if r['kind'] == 'incumbent':
            text = text.replace('supporting/previous-best/concept.md', 'candidates/' + a + '.md')
            text = text.replace('supporting/previous-best/finance-spec.json', 'specifications/' + a + '/finance-spec.json')
            text = text.replace('supporting/previous-best/first-launch.json', 'specifications/' + a + '/first-launch.json')
            text = text.replace('../001/selected.md', 'candidates/' + a + '.md')
    if redact_group_labels:
        for branch, label in group_labels.items():
            if label:
                text = re.sub(r'\b' + branch + r'\b', label, text)
    return text

def scrub_json(value):
    if isinstance(value, dict):
        return {neutral(k): scrub_json(v) for k, v in value.items()
                if k not in {'branch_id', 'parents', 'parent_candidates', 'parent_candidate_key',
                             'parent_key', 'parent_candidate', 'parent_policy', 'parent', 'lineage',
                             'money_provenance', 'coordinator_only'}}
    if isinstance(value, list):
        return [scrub_json(x) for x in value]
    return neutral(value) if isinstance(value, str) else value

def current_comparison_json(value):
    if isinstance(value, dict):
        return {k: current_comparison_json(v) for k, v in value.items()
                if k != 'old' and not k.startswith(('old_', 'parent_', 'delta_'))}
    if isinstance(value, list):
        return [current_comparison_json(v) for v in value]
    return value

def current_comparison_csv(content):
    reader = csv.DictReader(io.StringIO(content))
    columns = [c for c in reader.fieldnames
               if not c.startswith(('old_', 'parent_', 'delta_'))]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=columns, lineterminator='\n')
    writer.writeheader()
    for row in reader:
        writer.writerow({c: row[c] for c in columns})
    return output.getvalue()

for alias, record in aliases.items():
    source = (rd / record['origin_path']).resolve()
    specfolder = packet / 'specifications' / alias
    specfolder.mkdir()
    related = {}
    if record['kind'] == 'candidate':
        for item in source.parent.iterdir():
            if (item.is_file() and item != source and item.suffix != '.py'
                    and not item.name.startswith('self-check')
                    and not item.name.startswith('rework-')
                    and not item.name.endswith('validation.json')
                    and item.name not in {'concept.md', 'task.json', 'branch.json', 'changes.md', 'delta.md',
                                          'lineage.json', 'money-core-reuse.json', 'workload-comparison.csv',
                                          'file-contract-check.json', 'control-checks.json'}):
                target = specfolder / neutral(item.name)
                content = item.read_text()
                if item.suffix == '.json':
                    value = json.loads(content)
                    if item.name in {'payout-summary.json', 'workload-scenarios.json'}:
                        value = current_comparison_json(value)
                    save(target, scrub_json(value))
                else:
                    if item.name in {'money-examples.csv', 'edge-cases.csv'}:
                        content = current_comparison_csv(content)
                    target.write_text(neutral(content))
                related[item.resolve()] = target.resolve()
    elif record['kind'] == 'incumbent':
        projected = RUN / 'incumbent/finance-projection.json' if number == 1 else rd / 'supporting/previous-best/finance-spec.json'
        if projected.exists():
            target = specfolder / 'finance-spec.json'
            save(target, scrub_json(read(projected)))
            related[(source.parent / 'finance-spec.json').resolve()] = target.resolve()
        previous_assumptions = projected.parent / 'assumptions.csv'
        if previous_assumptions.exists():
            (specfolder / 'assumptions.csv').write_text(neutral(previous_assumptions.read_text()))
        for name in ['first-launch.json', 'first-launch.csv']:
            item = projected.parent / name
            if item.exists():
                if item.suffix == '.json':
                    save(specfolder / name, scrub_json(read(item)))
                else:
                    (specfolder / name).write_text(neutral(item.read_text()))

    text = source.read_text()
    if record['kind'] == 'incumbent':
        prior_alias = re.search(r'^Кандидат (V\d+)\b', text)
        if prior_alias:
            text = re.sub(r'\b' + prior_alias.group(1) + r'\b', alias, text)
    # Remove metadata/lineage statements, retain all mechanism and limitation text.
    text = '\n'.join(line for line in text.splitlines()
                     if not re.match(r'^\s*(?:Родител[ьи]|Предки|Ветка\s+[AB]\b|Автор\s*:|\*\*(?:Родител|Ветка))', line, re.I))
    text = re.sub(r'Lineage и подробная сверка изменений сохранены отдельно[^.]*\.', '', text)
    text = re.sub(r'(?:Lineage/сравнительный diff|История/lineage и сопоставление изменений) находятся отдельно[^.]*\.', '', text)
    text = text.replace('собственные записи только в ветке A', 'собственные записи только в рабочей папке')
    def link(m):
        label, target = m.group(1), m.group(2).strip('<>')
        if target.startswith(('https://', 'http://', '#')):
            return m.group(0)
        path = (source.parent / target.split('#')[0]).resolve()
        if path.name in {'changes.md', 'delta.md', 'lineage.json'}:
            return 'Сведения о происхождении исключены из первичной оценки.'
        if path in related:
            return '[' + label + '](' + str(related[path]) + ')'
        if path.name == 'finance-spec.json':
            return '[' + label + '](' + str(specfolder.resolve() / 'finance-spec.json') + ')'
        if path.name == 'assumptions.csv' and (specfolder / 'assumptions.csv').exists():
            return '[' + label + '](' + str(specfolder.resolve() / 'assumptions.csv') + ')'
        if path.name in {'first-launch.json', 'first-launch.csv'} and (specfolder / path.name).exists():
            return '[' + label + '](' + str(specfolder.resolve() / path.name) + ')'
        if path.name in {'context.md', 'baseline.md', 'evidence.md', 'diagnosis.md', 'rubric.json',
                         'synthetic-examples.json', 'synthetic-examples.md'}:
            return '[' + label + '](' + str(packet.resolve() / 'shared' / path.name) + ')'
        # Source locators remain project-root paths, not links to an author's working tree.
        try:
            location = str(path.relative_to(ROOT))
        except ValueError:
            location = str(path)
        return label + ' — `' + location + '`'
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', link, text)
    text = neutral(text)
    text = re.sub(r'Ветка\s+[AB]\s*[,.;:]?', '', text, flags=re.I)
    text = re.sub(r'родители\s*:\s*нет\.?', '', text, flags=re.I)
    (packet / 'candidates' / f'{alias}.md').write_text(f'Кандидат {alias}\n\n' + text + '\n')

for src in (rd / 'inputs').iterdir():
    if src.name == 'manifest.json':
        continue
    if src.suffix == '.json':
        save(packet / 'shared' / src.name, scrub_json(read(src)))
    else:
        (packet / 'shared' / src.name).write_text(neutral(src.read_text()))

for name in ['synthetic-examples.json', 'synthetic-examples.md']:
    source = rd / 'supporting' / name
    if source.exists():
        if source.suffix == '.json':
            save(packet / 'shared' / name, scrub_json(read(source)))
        else:
            (packet / 'shared' / name).write_text(neutral(source.read_text()))

finance = read(rd / 'checks/finance.json')
evidence = read(rd / 'checks/evidence.json')
# Keep current gates/findings, omit version provenance and source audit trails.
# Full unredacted checks remain in the round for the coordinator.
def review_checks(data, evidence_check=False):
    out = {'results': []}
    for result in data['results']:
        keep = ['candidate_key', 'status', 'scenario_scope', 'gates', 'assumption_refs', 'findings']
        current = {k: result[k] for k in keep if k in result}
        if evidence_check:
            for finding in current.get('findings', []):
                finding.pop('id', None)
                finding['locators'] = [x for x in finding.get('locators', [])
                                      if not any(t in x for t in ['provenance.json', '../001/checks/', 'private/'])]
                if 'text' in finding:
                    finding['text'] = finding['text'].replace('Prior concept matches provenance hash; selected neutral packaging has separately recorded expected hash. Policy unchanged.', '')
                    finding['text'] = finding['text'].replace('Prior QA98% still lacks exact new dictionary', 'QA98% lacks an exact dictionary')
                    finding['text'] = finding['text'].replace('not expanded comparably to new versions', 'not fully specified')
                    finding['text'] = finding['text'].replace('old operating-year conditional pass', 'operating-year conditional pass')
        out['results'].append(current)
    return scrub_json(out)
save(packet / 'checks.json', {'finance': review_checks(finance), 'evidence': review_checks(evidence, True)})
def report_links(text, source):
    def replace(m):
        label, target = m.group(1), m.group(2).strip('<>')
        if target.startswith(('http://', 'https://', '#')):
            return m.group(0)
        p = (source.parent / target.split('#')[0]).resolve()
        finance_root = (rd / 'checks/finance').resolve()
        if p.suffix == '.py' or p.name in {'source-manifest.json', 'delta-verification.json'}:
            return label + ' — технический исходник/аудит сохранён в полном отчёте координатора'
        if p.is_relative_to(finance_root):
            dest = packet / 'calculations' / neutral(str(p.relative_to(finance_root)))
        elif p.name in {'finance.json', 'evidence.json'} and p.parent == (rd / 'checks').resolve():
            dest = packet / 'checks.json'
        elif p.is_relative_to((rd / 'inputs').resolve()):
            dest = packet / 'shared' / p.name
        elif p.name in {'synthetic-examples.json', 'synthetic-examples.md'}:
            dest = packet / 'shared' / p.name
        else:
            for a, record in aliases.items():
                if p == (rd / record['origin_path']).resolve():
                    return '[' + label + '](' + str(packet / 'candidates' / (a + '.md')) + ')'
            try:
                location = str(p.relative_to(ROOT))
            except ValueError:
                location = str(p)
            return label + ' — `' + location + '`'
        return '[' + label + '](' + str(dest) + ')'
    return re.sub(r'\[([^\]]+)\]\(([^)]+)\)', replace, text)

for file in ['finance.md', 'evidence.md']:
    if (rd / 'checks' / file).exists():
        blind_report = rd / 'checks' / (Path(file).stem + '-for-review.md')
        if not blind_report.exists():
            blind_report = rd / 'checks' / Path(file).stem / (Path(file).stem + '-for-review.md')
        source = blind_report if blind_report.exists() else rd / 'checks' / file
        (packet / file).write_text(neutral(report_links(source.read_text(), source)))
for src in (rd / 'checks/finance').rglob('*'):
    if (src.is_file() and src.suffix in {'.json', '.csv', '.md'}
            and src.name not in {'source-manifest.json', 'delta-verification.json', 'finance-for-review.md'}):
        dest = packet / 'calculations' / neutral(str(src.relative_to(rd / 'checks/finance')))
        dest.parent.mkdir(parents=True, exist_ok=True)
        if src.suffix == '.json':
            save(dest, scrub_json(read(src)))
        else:
            dest.write_text(neutral(src.read_text()))

(packet / 'README.md').write_text('''# Независимое первичное ревью

Оценить каждого кандидата независимо по shared/rubric.json, затем сравнить.
Назначенные входы: candidates/, shared/, checks.json, finance.md, evidence.md,
calculations/ и specifications/. Ссылки на первичные источники можно проверять;
не читать private/, историю запусков, project/status.md, project/decisions.md,
исходные ветки или прежние review/selection. История/авторство не часть оценки.
Финансы пересчитаны на одной текущей основе; авторские старые проекции не заменяют checks.
Сценарный допуск отличается от реального внедрения. Допустимо отклонить всё.
Не запускать экспортирующие модели; самостоятельная read-only арифметика разрешена.
''')
hashes = {str(p.relative_to(packet)): hashlib.sha256(p.read_bytes()).hexdigest()
          for p in packet.rglob('*') if p.is_file()}
save(packet / 'manifest.json', {'files': hashes})
leaks = []
for p in packet.rglob('*'):
    if not p.is_file():
        continue
    text = p.read_text()
    for pattern in [r'CON-\d+(?:@v\d+|-v\d+)', r'branches/[AB]', r'incumbent', r'"branch_id"', r'предыдущ\w*\s+победител']:
        if re.search(pattern, text, re.I):
            leaks.append({'file': str(p.relative_to(packet)), 'pattern': pattern})
save(rd / 'private/packet-audit.json', {'files': len(hashes), 'identity_leaks': leaks, 'all_keys_covered': sorted(keymap), 'scope': 'Technical identity tokens and hashes; coordinator must check semantic fidelity.'})
print(json.dumps({'packet_files': len(hashes), 'identity_leaks': leaks}, ensure_ascii=False))
