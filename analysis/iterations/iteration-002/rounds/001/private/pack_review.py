from pathlib import Path
import json, re, hashlib, shutil, sys

r=Path(__file__).resolve().parent.parent
assert not (r/'snapshot.json').exists(), 'Sealed round cannot be repackaged'
mapping=json.loads((r/'private/review-map.json').read_text())['aliases']
bykey={v['candidate_key']:k for k,v in mapping.items()}
public=r/'review-packet'
assert not (public/'checks.json').exists() or '--rebuild' in sys.argv, 'Packet already assembled; inspect before overwrite'
assumptions={f'A{i:02d}':f'P{i:02d}' for i in range(1,8)} | {f'B{i:02d}':f'P{i+7:02d}' for i in range(1,7)}
(r/'private/assumption-map.json').write_text(json.dumps(assumptions,indent=2)+'\n')

def clean(s):
    # Strip ancestry metadata; preserve the mechanism and its objections.
    s=re.sub(r', родители \*\*[^\n]*?\*\*\.', '.', s)
    s=re.sub(r'родители:\s*`\[\]`\.', '', s, flags=re.I)
    s=s.replace('## 8. Наследование и условия отказа','## 8. Отличия и условия отказа')
    s=re.sub(r'^От CON-003.*?\n', 'Один акт объединяет обнаружение вклада, объяснение пользы и возникновение ограниченного права. Раздельные процедуры заменены одной записью; все старые основания будущего начисления не сохраняются.\n', s, flags=re.M)
    s=s.replace('Родителей нет. ', '')
    s=s.replace('A100percent new-C presentation sensitivity', '100percent new-C presentation sensitivity')
    for old,new in assumptions.items():
        s=re.sub(r'\b'+old+r'\b',new,s)
    for key,alias in sorted(bykey.items(),key=lambda kv:-len(kv[0])):
        item=mapping[alias]
        s=s.replace(str(r/item['origin_path']), 'review-packet/candidates/'+alias+'.md')
        if item['kind']=='candidate':
            s=s.replace('analysis/iterations/iteration-002/rounds/001/'+item['origin_path'], 'review-packet/candidates/'+alias+'.md')
            s=s.replace(item['origin_path'],'review-packet/candidates/'+alias+'.md')
        s=s.replace(key,alias)
        if key.startswith('CON-'):
            s=s.replace(key.split('@')[0],alias)
    s=s.replace('checks/finance/', 'review-packet/finance/')
    s=s.replace('checks/evidence/', 'review-packet/evidence/')
    aa=bykey['CON-005@v1'];bb=bykey['CON-006@v1']
    s=s.replace(';005;006',';'+aa+';'+bb)
    s=re.sub(r'\bA(?=,\s*строки)',aa,s)
    s=re.sub(r'\bB(?=,\s*строки)',bb,s)
    s=s.replace('B прямо раскрывает',bb+' прямо раскрывает')
    s=re.sub(r'\bA:(?=\d)',aa+':',s)
    s=re.sub(r'\bB:(?=\d)',bb+':',s)
    return s

for alias,item in mapping.items():
    (public/'candidates'/f'{alias}.md').write_text(clean((r/item['origin_path']).read_text()))

for label in ['finance','evidence']:
    source=r/'checks'/label
    if source.is_dir():
        for p in source.rglob('*'):
            if not p.is_file() or '__pycache__' in p.parts or p.suffix in {'.pyc','.DS_Store'}:
                continue
            if p.name.startswith('verify_') and p.suffix=='.py':
                continue
            dest=public/label/p.relative_to(source)
            dest.parent.mkdir(parents=True,exist_ok=True)
            if p.suffix.lower() in {'.md','.json','.csv','.tsv','.txt','.py'}:
                body=p.read_text(encoding='utf-8-sig')
                if label=='finance' and p.name=='model.py':
                    body=body.split('\ndef author_checks(',1)[0]+'\n# Arithmetic functions retained; administrative original-path validation is excluded from this review copy.\n'
                if label=='finance' and p.name=='finance-report.md':
                    body=re.sub(r'Независимый код написан.*?(?=## Сопоставимость)', 'Независимая модель выполнена в первоначальной области проверки. Пересчитаны 3×8 сценариев первого года и CORE второго года: 27 годовых строк, 324 месячных снимка, 208 числовых ячеек заявленных таблиц. Хеши пяти frozen inputs и двух версий проверены. В этой копии model.py сохранены расчётные функции для чтения и независимого пересчёта; административные функции первоначальных путей и экспорта исключены. Таблицы и validation отражают выполненный оригинал, а не новый запуск этой текстовой копии. CSV сохраняют единицы в именах столбцов.\n\n', body, flags=re.S)
                if label=='evidence' and p.name=='evidence-report.md':
                    body=re.sub(r'; воспроизведение из корня:.*?Скрипт пишет только свой `source-checks.json`\.', '. Административный скрипт проверки первоначальных путей не включён в эту копию; результаты и проверенные цитаты сохранены в source-checks.json.', body, flags=re.S)
                dest.write_text(clean(body))
            else:
                shutil.copyfile(p,dest)

checks={}
for label in ['finance','evidence']:
    data=json.loads(clean((r/'checks'/f'{label}.json').read_text()))
    for row in data['results']:
        row['alias']=row.pop('candidate_key')
    checks[label]=data
(public/'checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n')

readme='''# Пакет независимой оценки

Назначенные входы: candidates/*.md, checks.json, finance/**, evidence/** и пять общих inputs/*. Кандидаты обозначены только псевдонимами. Предыдущие ранги, авторство и происхождение не входят в пакет. Приватные/служебные файлы за его пределами не читать.

Все проектные пути источников knowledge/... считаются от корня OTP_bank; inputs/ — от папки раунда. Пути review-packet/ также считаются от раунда. Внутри finance/evidence относительные пути приложений считаются от соответствующей папки.

Статусы экономики относятся только к явно проверенным сценариям/границам. Проверка фактического банковского бюджета и условий внедрения отдельно неизвестна. Нет заданного предпочтения или обязательного победителя; оценить все варианты и допускается отклонить все. Контроль также оценивается, но не выбирается как новая рекомендация.

В копиях заменены обозначения и служебные пути; расчётные числа и существенные ограничения сохранены. Хеши execution-оригиналов в приложениях относятся к первоначальному запуску, а не к текстовым копиям после замены идентификаторов. packet-manifest.json фиксирует текущие публичные копии. Полные неизменённые оригиналы сохраняет координатор для аудита.

В finance/model.py сохранены расчётные функции. Административные проверки первоначальных путей вынесены из этой копии; её нельзя выдавать за неизменённый полный execution-оригинал. Результаты проверок и все расчётные таблицы приложены.
'''
(public/'README.md').write_text(readme)
leaks=[]
for p in public.rglob('*'):
    if p.is_file() and p.suffix in {'.md','.json','.csv','.tsv','.txt','.py'}:
        t=p.read_text(encoding='utf-8-sig')
        found=re.findall(r'CON-\d+(?:@v\d+)?|branches/[AB]|родители|Наследование',t,re.I)
        if found: leaks.append({'file':str(p.relative_to(public)),'matches':sorted(set(found))})
manifest={str(p.relative_to(public)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(public.rglob('*')) if p.is_file() and p.name!='packet-manifest.json'}
(public/'packet-manifest.json').write_text(json.dumps({'sha256':manifest},ensure_ascii=False,indent=2)+'\n')
(r/'private/packet-audit.json').write_text(json.dumps({'files':len(manifest),'identifier_scan_leaks':leaks,'sha256':manifest},ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'files':len(manifest),'leaks':leaks},ensure_ascii=False))
if leaks: raise SystemExit('Inspect leaks before reviewer dispatch')
