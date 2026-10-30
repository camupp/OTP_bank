"""Build anonymous checks after independent checks finish; no concept edits."""
from pathlib import Path
import csv, hashlib, json, re
R=Path(__file__).resolve().parents[1]
P=R/'review-packet'
M=json.loads((R/'private/review-map.json').read_text())['aliases']
KEYS={v['candidate_key']:k for k,v in M.items()}

def scrub(s):
    for key,alias in sorted(KEYS.items(),key=lambda x:-len(x[0])):
        s=s.replace(key,alias)
    s=re.sub(r'analysis/iterations/iteration-004/rounds/001/branches/A/[^\s`\)\]"\n]+','досье V03',s)
    s=re.sub(r'analysis/iterations/iteration-004/rounds/001/branches/B/[^\s`\)\]"\n]+','досье V01',s)
    s=re.sub(r'(?:analysis/iterations/iteration-004/)?incumbent/[^\s`\)\]"\n]+','досье V02',s)
    s=s.replace('branches/A','V03').replace('branches/B','V01')
    s=re.sub(r'incumbent','V02',s,flags=re.I)
    s=re.sub(r'\bB_','V01_',s)
    s=re.sub(r'(?<![\w/.-])baseline(?![\w/.-])','V04',s,flags=re.I)
    s=re.sub(r'\bA\b','V03',s)
    s=re.sub(r'\bB\b','V01',s)
    s=re.sub(r'\b[AB]([0-9]{2})\b',r'P\1',s)
    s=s.replace('прежний победитель','вариант V02').replace('предыдущий победитель','вариант V02')
    s=s.replace('неизменённый V02','V02').replace('сохранённый V02','V02')
    s=s.replace('iteration-003','общая база источника')
    s=s.replace('inputs/baseline.md','shared/baseline.md')
    s=s.replace('inputs/context.md','shared/context.md')
    s=s.replace('inputs/evidence.md','shared/evidence.md')
    s=s.replace('inputs/diagnosis.md','shared/diagnosis.md')
    s=s.replace('(finance/','(calculations/')
    return s

def anon(obj):
    if isinstance(obj,str):return scrub(obj)
    if isinstance(obj,list):return [anon(x) for x in obj]
    if isinstance(obj,dict):return {('alias' if k=='candidate_key' else scrub(k)):anon(v) for k,v in obj.items()}
    return obj

(P/'calculations').mkdir(exist_ok=True)
for src in sorted((R/'checks/finance').iterdir()):
    if not src.is_file() or src.suffix not in ['.csv','.json'] or src.name=='source-manifest.json':continue
    if src.suffix=='.json':
        (P/'calculations'/src.name).write_text(json.dumps(anon(json.loads(src.read_text())),ensure_ascii=False,indent=2)+'\n')
    else:(P/'calculations'/src.name).write_text(scrub(src.read_text()))
f=anon(json.loads((R/'checks/finance.json').read_text()))
e=anon(json.loads((R/'checks/evidence.json').read_text()))
e.pop('checked_versions_sha256',None)
e['note_path']='evidence.md'
for row in e['results']:
    row['evidence_refs']=[x for x in row['evidence_refs'] if not any(t in x for t in ['provenance','общая база источника/rounds','досье V02'])]
    row['findings']=[x for x in row['findings'] if not any(t in x.lower() for t in ['byte-identical','old m01/m02'])]
    row['findings']=[x.replace('this unchanged concept','this concept') for x in row['findings']]
for row in f['results']:
    row['calculation_paths']=['calculations/'+Path(x).name for x in row.get('calculation_paths',[]) if (P/'calculations'/Path(x).name).is_file()]
(P/'checks.json').write_text(json.dumps({'finance':f,'evidence':e,'scope':'Same declared M04 scenarios; separate common resource sensitivity; no measured effect or bank rollout approval'},ensure_ascii=False,indent=2)+'\n')
note=scrub((R/'checks/finance.md').read_text())
note=note.replace('[model.py](calculations/model.py)','собственным воспроизводимым расчётом')
note=note.replace('[source-manifest.json](calculations/source-manifest.json)','реестр хешей проверенных источников')
note=note.replace('[finance.json](finance.json)','[checks.json](checks.json)')
note=re.sub(r'Запуск из любой папки:.*?Полный контракт:', 'Проверка исходной модели завершена; приложены обезличенные таблицы. Полный контракт:',note)
(P/'finance.md').write_text(note)
note='# Точечная проверка доказательств\n\n31.10.2026. Проверены все четыре описания. Критических фактических ошибок не выявлено. Supported относится к фактическому описанию; partial — к ограниченной переносимости/неизвестным реальным условиям, а не к требованию доказать каждую гипотезу.\n\nГлубина: визуально PDF10,14,15,19; fixed11–12 по ранее сверенной выжимке; T1335 по сохранённой преобразованной строке, без повторной диагностики Excel; выбранные строки Transcript и переписки организаторов. Внешние правила R01–R07 проверены по первичным страницам в указанной в shared/evidence.md глубине. Абстрактные исследования — только сохранённые аннотации, не полный текст. Эффект для ОТП не установлен.\n'
for row in e['results']:
    note+='\n## '+row['alias']+' — '+row['status']+'\n\n'+'\n'.join('- '+x for x in row['findings'])+'\n'
note+='\nТочные первичные URL и locators — [общая доказательная основа](shared/evidence.md). Финансовые gates проверены отдельно и не отменяются этим заключением.\n'
(P/'evidence.md').write_text(note)
for name in ['V01.md','V02.md','V03.md','V04.md']:
    src=P/'candidates'/name
    s=src.read_text()
    if 'Сопоставимые результаты: [независимые проверки]' not in s:
        s+='\n\nСопоставимые результаты: [независимые проверки](../checks.json), [финансовая записка](../finance.md), [проверка источников](../evidence.md), [годовые расчёты](../calculations/annual.csv), [сопоставимая стоимость](../calculations/comparable-costs.csv). Числа авторской иллюстрации при расхождении оцениваются по независимой общей проверке; механизм не меняется.\n'
    src.write_text(s)
files={str(x.relative_to(P)):hashlib.sha256(x.read_bytes()).hexdigest() for x in sorted(P.rglob('*')) if x.is_file() and x.name!='manifest.json'}
(P/'manifest.json').write_text(json.dumps({'files':files,'rubric_sha256':hashlib.sha256((P/'shared/rubric.json').read_bytes()).hexdigest(),'reviewer_has_no_identity_map':True},ensure_ascii=False,indent=2)+'\n')
forbidden=[]
for x in P.rglob('*'):
    if not x.is_file():continue
    text=x.read_text()
    for pat in [r'CON-\d+',r'branches/[AB]',r'incumbent',r'\bB_',r'H-B2',r'lineage',r'прежний победитель',r'предыдущий победитель']:
        if re.search(pat,text):forbidden.append({'path':str(x.relative_to(P)),'pattern':pat})
assert not forbidden,forbidden
(R/'private/packet-audit.json').write_text(json.dumps({'status':'pass','identity_leaks':forbidden,'files':len(files),'fidelity_audit':'private/packet-fidelity-audit.md','resolution':'private/packet-fidelity-resolution.md','neutral_finance_and_evidence':True},ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':'pass','files':len(files),'aliases':list(M)},ensure_ascii=False))
