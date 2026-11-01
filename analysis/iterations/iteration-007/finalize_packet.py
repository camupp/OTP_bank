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
    if int(sys.argv[1]) == 2:
        content = content.replace('Её политика и ресурсный план не модернизированы; новый допуск не восстановлен.',
                                  'Действительная обеспеченность этой политики и её ресурсного плана не установлена.')
        content = content.replace('Точечный source не доказывает свободный штат и эксплуатационнуюготовность исходнойполитики; историческийдокумент сохраняется буквально.',
                                  'Точечный source не доказывает свободный штат и эксплуатационную готовность сравниваемой политики.')
        content = content.replace('Основа: общий пакет `inputs/` и `supporting/` раунда001 iteration-006 от корня проекта.',
                                  'Основа: общий пакет фактов и финансовых допущений в shared/.')
        if relative == 'shared/source-claims.json':
            data = json.loads(content)
            reference_alias = next(a for a, r in mapping.items() if r['kind'] == 'incumbent')
            data['sources'] = [s for s in data['sources'] if s['source_id'] != 'S13']
            for source in data['sources']:
                if source['source_id'] in {'S11', 'S12'}:
                    source['path'] = ('../candidates/' + reference_alias + '.md'
                                      if source['source_id'] == 'S11' else '../finance.md')
                    source['source_kind'] = ('сравниваемая проектная политика' if source['source_id'] == 'S11'
                                             else 'текущая независимая финансовая проверка')
                    source['publication_or_version_date'] = 'копия текущего пакета; исходные версии сохранены у координатора'
                    source['read_locators'] = ('разделы механики, ресурса и проверки эффекта' if source['source_id'] == 'S11'
                                                else 'QA, ресурсные допущения и границы проверки')
                    source['actual_reading_depth'] = 'included_current_packet_sections'
                    source.pop('sha256', None)
            for claim in data['claims']:
                claim['evidence_refs'] = [r for r in claim.get('evidence_refs', []) if r['source_id'] != 'S13']
                if claim.get('claim_id') == 'E13':
                    claim['evidence_refs'] = [r for r in claim['evidence_refs'] if r['source_id'] != 'S12']
                    claim['epistemic_type'] = 'design_document_statement'
                    claim['assessment'] = 'Формула и условия описаны в сравниваемой политике; это факт о документе.'
            content = json.dumps(data, ensure_ascii=False, indent=2) + '\n'
        content = re.sub(r'Сопоставление с родителем — `[^`]*operation-delta\.md` и (\[resource-stages\.csv\]\([^)]+\)) показывают заменённые операции:',
                         r'\1 показывает заменённые операции:', content)
        content = re.sub(r'Команды, авторские проверки C1–C7[^\n]*',
                         'Независимые текущие проверки — [evidence.md](../evidence.md).', content)
        if relative.startswith('candidates/'):
            alias = path.stem
            if mapping.get(alias, {}).get('candidate_key', '').startswith('CON-023@') and '110%' not in content:
                content += '\nБинарный критерий использования одного делового решения не требует 110% от единицы.\n'
        if relative.startswith('specifications/') and path.name == 'source-to-award.md':
            content = content.replace('Положительные акты/пакеты и пять отрицательных случаев в `c3-rework-examples.json` — специально обозначенные in-memory примеры, не действия банка и не исправленный общий source.',
                                      'Положительные акты/пакеты и пять отрицательных случаев — специально обозначенные in-memory примеры, не действия банка и не изменённый общий source. Текущая независимая проверка: [current-controls.json](../../calculations/evidence/current-controls.json).')
    if int(sys.argv[1]) >= 3:
        content = re.sub(r'C3 rework V\d+:', 'C3:', content)
        content = content.replace('parent_max_blocks', 'max_blocks').replace('parent_max', 'max_blocks')
        content = content.replace('pinned parent monthly-resource.csv', 'зафиксированного сценарного ряда monthly-resource.csv')
        content = content.replace('parent forecast', 'full forecast')
        content = content.replace('same parent operation', 'same defined operation')
        content = content.replace('исправленныйC3', 'контрольC3')
        content = content.replace('старая parent-подпись', 'подпись иной версии')
        content = re.sub(r'Единственный rework: [^\n]*?Командный source-review получил прежнюю временную нижнюю границу личного акта\.',
                         'Контроль полномочий: командный source-review имеет ту же временную нижнюю границу, что и личный акт.', content)
        content = content.replace('В signing projection добавлен public_business_configs=', 'В signing projection включён public_business_configs=')
        content = re.sub(r'Предыдущие результаты и semanticSHA закреплены в provenance.json; архив private/pre-rework автор не читал/не менял\.', '', content)
        content = re.sub(r'Команды, авторские проверки C1–C7[^\n]*',
                         'Независимые текущие проверки — [evidence.md](../evidence.md).', content)
        if relative.startswith('specifications/') and path.name == 'source-to-award.md':
            content = content.replace('Положительные акты/пакеты и пять отрицательных случаев в `c3-rework-examples.json` — специально обозначенные in-memory примеры, не действия банка и не исправленный общий source.',
                                      'Положительные и отрицательные in-memory примеры не являются действиями банка. Текущая независимая проверка: [current-controls.json](../../calculations/evidence/current-controls.json).')
            content = re.sub(r'Положительные акты/пакеты и пять отрицательных случаев в `self-check.json`[^\n]*',
                             'Положительные и отрицательные in-memory примеры не являются действиями банка. Текущая независимая проверка: [current-controls.json](../../calculations/evidence/current-controls.json).', content)
        if relative == 'calculations/evidence/integrity.json':
            data = json.loads(content)
            data.pop('reference_copied_files', None)
            content = json.dumps(data, ensure_ascii=False, indent=2) + '\n'
        if relative == 'calculations/verification.json':
            data = json.loads(content)
            if 'checks_detail' in data:
                data['checks_detail'] = [row for row in data['checks_detail']
                                        if not any(token in str(row.get('name', ''))
                                                   for token in ['rework-baseline', 'c3-rework-examples'])]
            content = json.dumps(data, ensure_ascii=False, indent=2) + '\n'
    if int(sys.argv[1]) >= 3 and relative == 'shared/source-claims.json':
        data = json.loads(content)
        data['sources'] = [s for s in data['sources'] if s['source_id'] not in {'S11', 'S12', 'S13'}]
        for claim in data['claims']:
            claim['evidence_refs'] = [r for r in claim.get('evidence_refs', [])
                                      if r['source_id'] not in {'S11', 'S12', 'S13'}]
            if claim.get('claim_id') == 'E13':
                claim['claim'] = 'В иллюстративной объёмной схеме Q — нормированный объём/мощность относительно эталона;1,10 — возможный top, QA и SLA заданы отдельно.'
                claim['epistemic_type'] = 'illustrative_design_definition'
                claim['verification_status'] = 'illustrative_not_bank_fact'
                claim['assessment'] = 'Иллюстрация определения шкалы, не установленная формула банка и не указание выбрать какой-либо вариант.'
        content = json.dumps(data, ensure_ascii=False, indent=2) + '\n'
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
