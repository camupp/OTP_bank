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
    source_versions = {}
    def protect_source_version(match):
        token = '__COMMON_SOURCE_VERSION_' + str(len(source_versions)) + '__'
        source_versions[token] = match.group(0)
        return token
    text = re.sub(r'OTP-SYN-[A-Za-z0-9-]+-v\d+', protect_source_version, text)
    for key in sorted(keymap, key=len, reverse=True):
        text = text.replace(key, keymap[key])
        text = text.replace(key.replace('@', '-'), keymap[key])
        text = text.replace(key.replace('-', '').replace('@', ''), keymap[key])
    text = re.sub(r'CON-\d+(?:@v\d+|-v\d+)', 'variant', text)
    text = re.sub(r'incumbent', 'reference', text, flags=re.I)
    text = re.sub(r'Текущий неизменённый контроль\s*V\d+', 'Сравниваемая программа', text)
    text = re.sub(r'ТекущийнеизменённыйконтрольV\d+', 'Сравниваемая программа', text)
    text = re.sub(r'branches/[AB]', 'specifications', text)
    text = text.replace('v1_total_hours_month', 'declared_primary_qa_hours_month')
    text = re.sub(r'\bv[1-9]\d*\b', 'редакция', text)
    text = re.sub(r'finance-spec-\d+\.json', 'finance-spec.json', text)
    text = re.sub(r'assumptions-\d+\.csv', 'assumptions.csv', text)
    text = text.replace('supporting/synthetic-examples.', 'shared/synthetic-examples.')
    text = text.replace('supporting/fixtures/', 'shared/fixtures/')
    text = text.replace('supporting/measurement-contract.md', 'shared/measurement-contract.md')
    text = text.replace('supporting/finance-basis/', 'shared/finance-basis/')
    text = text.replace('supporting/round002-stress/', 'shared/round002-stress/')
    text = text.replace('supporting/resource-menu.json', 'shared/resource-menu.json')
    text = text.replace('supporting/round002-common-assumptions.md', 'shared/round002-common-assumptions.md')
    text = text.replace('supporting/qa-neighborhood-recipe.json', 'shared/qa-neighborhood-recipe.json')
    text = re.sub(r'Денежный core006[^\n]*',
                  'Общие денежные параметры и календарь проверены отдельно в финансовом отчёте. '
                  'Синтетический расчёт не доказывает готовность банка или причинный эффект.', text)
    text = text.replace('слабости награды/ожидания006', 'слабости размера награды и ожидания')
    text = text.replace('модели006', 'сравниваемой модели')
    if number >= 2:
        text = text.replace('По сравнению с018 не урезаны минуты, добавлены контроль локальной цели и оплаченный резерв; отсутствующий bundle021 не синтезирован.',
                            'Контроль локальной цели и оплаченный резерв включены; отсутствующее подтверждение потока не считается полученным.')
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
    for token, version in source_versions.items():
        text = text.replace(token, version)
    return text

def scrub_json(value):
    if isinstance(value, dict):
        return {neutral(k): scrub_json(v) for k, v in value.items()
                if k not in {'branch_id', 'parents', 'parent_candidates', 'parent_candidate_key',
                             'parent_key', 'parent_candidate', 'parent_policy', 'parent', 'lineage',
                             'money_provenance', 'version_provenance', 'source_sha256', 'coordinator_only',
                             'source_sha256_new', 'inherited_core_locators', 'output_paths',
                             'measurement_override', 'inherited_money_core', 'inherited_reward_core',
                             'inherited_reward_policy', 'reward_core', 'metric_text_overrides',
                             'rule_version'}}
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
                    and not item.name.startswith(('artifact', 'inheritance'))
                    and not item.name.endswith('validation.json')
                    and item.name not in {'concept.md', 'task.json', 'branch.json', 'changes.md', 'delta.md',
                                          'lineage.json', 'money-core-reuse.json', 'workload-comparison.csv',
                                          'file-contract-check.json', 'control-checks.json',
                                          'verification.json', 'source-manifest.json',
                                          'signature-counterexample.json', 'artifact-manifest.json',
                                          'artifacts.sha256.json', 'completion-report.md',
                                          'operation-delta.md', 'c3-rework-examples.json',
                                          'provenance.json', 'parent-reuse.json', 'resource-reference.json',
                                          'rank-delta.csv', 'booking-delta.csv'}):
                target = specfolder / neutral(item.name)
                content = item.read_text()
                if item.suffix == '.json':
                    value = json.loads(content)
                    if item.name in {'payout-summary.json', 'workload-scenarios.json'}:
                        value = current_comparison_json(value)
                    value = scrub_json(value)
                    if item.name == 'finance-spec.json' and isinstance(value.get('calendar'), dict):
                        value['calendar']['source'] = '../../shared/common-money-calendar.csv'
                    save(target, value)
                else:
                    if item.name in {'money-examples.csv', 'edge-cases.csv'}:
                        content = current_comparison_csv(content)
                    target.write_text(neutral(content))
                related[item.resolve()] = target.resolve()
        reference = source.parent / 'resource-reference.json'
        if reference.exists():
            pinned = read(reference)
            for name, entry in pinned['files'].items():
                target = specfolder / name
                if target.exists():
                    continue
                original = ROOT / entry['project_path']
                assert hashlib.sha256(original.read_bytes()).hexdigest() == entry['sha256']
                target.write_text(neutral(original.read_text().replace(pinned['parent'], record['candidate_key'])))
    elif record['kind'] == 'incumbent':
        projected = RUN / 'incumbent/finance-spec.json' if number == 1 else rd / 'supporting/previous-best/finance-spec.json'
        if projected.exists():
            target = specfolder / 'finance-spec.json'
            value = scrub_json(read(projected))
            if isinstance(value.get('calendar'), dict):
                value['calendar']['source'] = '../../shared/common-money-calendar.csv'
            save(target, value)
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
        if number >= 3:
            # A later incumbent needs the same current specifications as new candidates.
            for item in projected.parent.iterdir():
                if (not item.is_file() or item.suffix == '.py'
                        or item.name.startswith(('self-check', 'rework-', 'artifact', 'inheritance'))
                        or item.name in {'concept.md', 'README.md', 'completion-report.md',
                                         'operation-delta.md', 'c3-rework-examples.json',
                                         'lineage.json', 'changes.md', 'provenance.json',
                                         'parent-reuse.json', 'rank-delta.csv', 'booking-delta.csv'}):
                    continue
                target = specfolder / neutral(item.name)
                if item.suffix == '.json':
                    save(target, scrub_json(read(item)))
                else:
                    target.write_text(neutral(item.read_text()))

    text = source.read_text()
    if number >= 3:
        text = re.sub(r'(?:Родитель CON-022@v1 объединял|Историческая основа CON-022@v1 объединяла)[^\n]*?фиксированными категориями наблюдаемого штрафа;',
                      'Ранг задан фиксированными категориями наблюдаемого штрафа;', text)
        text = text.replace('Непосредственный родитель CON-023@v2; механизм признания и C3 сохранены.',
                            'Механизм признания и контроль полномочий описаны ниже.')
        text = text.replace('Непосредственный родитель CON-023@v2. Новое отличие —', 'Принят подход:')
        text = text.replace('Личные суммы/ожидания и правила normal/strong остаются как у CON-023@v2.',
                            'Личные суммы/ожидания и правила normal/strong заданы текущими карточками.')
        text = re.sub(r'\[Сопоставление с родителем\]\(operation-delta.md\) и (\[resource-stages.csv\]\([^)]+\)) показывают',
                      r'\1 показывает', text)
        text = re.sub(r'Сохранённый результат CON-024@v1:[^\n]*?Новая version/rule hash',
                      'Текущие вычисленные результаты проверены независимо. Новая version/rule hash', text)
        text = re.sub(r'Полные pin/lineage/нулевая экономическая дельта — \[provenance.json\]\(provenance.json\)\.',
                      'Техническое происхождение сохранено у координатора.', text)
        text = re.sub(r'## 8\.[^\n]+', '## 8. Наблюдения, ограничения и условия отклонения', text)
    if record['kind'] == 'incumbent':
        prior_alias = re.search(r'^Кандидат (V\d+)\b', text)
        if prior_alias:
            text = re.sub(r'\b' + prior_alias.group(1) + r'\b', alias, text)
    # Remove metadata/lineage statements, retain all mechanism and limitation text.
    text = '\n'.join(line for line in text.splitlines()
                     if not re.match(r'^\s*(?:Родител[ьи]|Предки|Ветка\s+[AB]\b|Автор\s*:|\*\*(?:Родител|Ветка))', line, re.I))
    text = re.sub(r'Lineage и подробная сверка изменений сохранены отдельно[^.]*\.', '', text)
    text = re.sub(r'(?:Lineage/сравнительный diff|История/lineage и сопоставление изменений) находятся отдельно[^.]*\.', '', text)
    if number >= 2:
        # Omit ancestry paragraphs; all present rules and rejection conditions remain.
        text = '\n\n'.join(paragraph for paragraph in text.split('\n\n')
                           if not paragraph.startswith(('Родитель CON-', 'От018 сохранены',
                                                        'Непосредственный родитель этой версии')))
        text = re.sub(r'## 8\. (?:Отличие от родителя и условия отклонения|Отличия от родителей и отказ)',
                      '## 8. Ограничения и условия отклонения', text)
    text = text.replace('собственные записи только в ветке A', 'собственные записи только в рабочей папке')
    def link(m):
        label, target = m.group(1), m.group(2).strip('<>')
        if target.startswith(('https://', 'http://', '#')):
            return m.group(0)
        path = (source.parent / target.split('#')[0]).resolve()
        if path.name in {'changes.md', 'delta.md', 'lineage.json', 'provenance.json', 'parent-reuse.json'}:
            return 'Сведения о происхождении исключены из первичной оценки.'
        if path in related:
            return '[' + label + '](' + str(related[path]) + ')'
        if (specfolder / path.name).is_file():
            return '[' + label + '](' + str(specfolder.resolve() / path.name) + ')'
        if path.name == 'resource-reference.json' and (specfolder / 'monthly-resource.csv').is_file():
            return '[monthly-resource.csv](' + str(specfolder.resolve() / 'monthly-resource.csv') + ')'
        if record['kind'] == 'incumbent' and path.name == 'evidence.md' and label == 'evidence.md':
            return '[' + label + '](' + str(packet.resolve() / 'evidence.md') + ')'
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

for name in ['measurement-contract.md', 'source-evidence-brief.md', 'source-claims.json',
             'reward-basis.md', 'employee-profiles.md', 'resource-menu.json',
             'round002-common-assumptions.md', 'qa-neighborhood-recipe.json']:
    src = rd / 'supporting' / name
    if not src.exists():
        continue
    if src.suffix == '.json':
        save(packet / 'shared' / name, scrub_json(read(src)))
    else:
        (packet / 'shared' / name).write_text(neutral(src.read_text()))
money_calendar = RUN / 'incumbent/first-launch.csv'
if money_calendar.exists():
    (packet / 'shared/common-money-calendar.csv').write_bytes(money_calendar.read_bytes())
for name in ['scenario-inputs.json', 'annual-three-year.csv', 'basis.md']:
    src = rd / 'supporting/finance-basis' / name
    if src.exists():
        dest = packet / 'shared/finance-basis' / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        if src.suffix == '.json':
            save(dest, scrub_json(read(src)))
        else:
            dest.write_text(neutral(src.read_text()))

for name in ['synthetic-examples.json', 'synthetic-examples.md']:
    source = rd / 'supporting' / name
    if source.exists():
        if source.suffix == '.json':
            save(packet / 'shared' / name, scrub_json(read(source)))
        else:
            (packet / 'shared' / name).write_text(neutral(source.read_text()))

# Source-only fixture copy for independent review, never evaluator oracle or generator.
fixture = rd / 'supporting/fixtures'
if fixture.exists():
    import shutil
    for directory in ['source', 'patches']:
        shutil.copytree(fixture / directory, packet / 'shared/fixtures' / directory)
    for name in ['dictionary.md', 'assumptions.csv']:
        (packet / 'shared/fixtures' / name).write_text(neutral((fixture / name).read_text()))
    (packet / 'shared/fixtures/README.md').write_text('Общие синтетические источники. Все записи вымышлены. source/reader.py раскрывает base и patches по source/scenario_index.json. Oracle и генератор не предоставлены; не читать их вне пакета. Показатели/выплаты в данных не заданы. Все варианты получают одинаковые поля. Даты/нормы/штат не наблюдения банка. У каждого исхода сохранять источники, знаменатели и достаточность данных.\n')

addendum = rd / 'supporting/round002-stress'
if addendum.exists():
    public_manifest = read(addendum / 'manifest.json')
    for member in public_manifest['files']:
        source = addendum / member['path']
        target = packet / 'shared/round002-stress' / member['path']
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
    for name in ['manifest.json', 'manifest.sha256']:
        if (addendum / name).exists():
            (packet / 'shared/round002-stress' / name).write_bytes((addendum / name).read_bytes())

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
            and not src.name.startswith('delta-')
            and src.name not in {'source-manifest.json', 'delta-verification.json', 'finance-for-review.md'}):
        dest = packet / 'calculations' / neutral(str(src.relative_to(rd / 'checks/finance')))
        dest.parent.mkdir(parents=True, exist_ok=True)
        if src.suffix == '.json':
            save(dest, scrub_json(read(src)))
        else:
            dest.write_text(neutral(src.read_text()))

for src in (rd / 'checks/evidence').rglob('*'):
    if (src.is_file() and src.suffix in {'.json', '.csv', '.md'}
            and not src.name.startswith('delta-')
            and src.name not in {'source-manifest.json', 'evidence-for-review.md',
                                 'counterexamples.json', 'c3-probes.json', 'a-c3-specific.json',
                                 'current-delta-verification.json', 'metric-invariance.json'}):
        dest = packet / 'calculations/evidence' / neutral(str(src.relative_to(rd / 'checks/evidence')))
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
baseline_alias = next(a for a, r in aliases.items() if r['kind'] == 'baseline')
with (packet / 'README.md').open('a') as handle:
    handle.write('\nДействующая программа кейса — ' + baseline_alias
                 + '. Оценить её по той же рубрике, но не включать в shortlist новой рекомендации.\n')
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
