"""Build neutral assigned copies; private alias map stays outside review packet."""
from pathlib import Path
import json,re,hashlib,shutil
R=Path(__file__).resolve().parents[1]
P=R/'review-packet'
MAP={
 'V01':{'candidate_key':'CON-006@v2','kind':'candidate','origin_path':'branches/B/concept.md'},
 'V02':{'candidate_key':'CON-005@v1','kind':'incumbent','origin_path':'../../incumbent/concept.md'},
 'V03':{'candidate_key':'BASELINE','kind':'baseline','origin_path':'inputs/baseline.md'},
 'V04':{'candidate_key':'CON-005@v2','kind':'candidate','origin_path':'branches/A/concept.md'},
}
keys={v['candidate_key']:a for a,v in MAP.items()}
pathmap={
 'analysis/iterations/iteration-003/incumbent/concept.md':'candidates/V02.md',
 '../../incumbent/concept.md':'candidates/V02.md',
 'analysis/iterations/iteration-002/rounds/001/branches/A/concept.md':'candidates/V02.md',
 'branches/A/concept.md':'candidates/V04.md','branches/B/concept.md':'candidates/V01.md',
 'branches/A/finance-spec.json':'specifications/V04.json','branches/B/policy-spec.json':'specifications/V01.json',
 'analysis/iterations/iteration-003/rounds/001/inputs/':'inputs/',
 'analysis/iterations/iteration-002/rounds/001/inputs/':'inputs/',
 'branches/A/':'support/V04/','branches/B/':'support/V01/',
}
def scrub(s):
 for old,new in sorted(pathmap.items(),key=lambda x:-len(x[0])):s=s.replace(old,new)
 for old,new in sorted(keys.items(),key=lambda x:-len(x[0])):s=s.replace(old,new)
 s=re.sub(r'CON-\d+@v\d+','другая спецификация',s)
 s=re.sub(r'\b(?:A2-|B2-)(\d+)','P-\\1',s)
 s=re.sub(r'\bA0([1-9])\b',r'P0\1',s)
 s=re.sub(r'неизмен[её]нн(?:ая|ой|ую) верси(?:я|и|ю)', 'спецификация',s,flags=re.I)
 s=s.replace('unchanged version','specification').replace('unchanged CON','specification CON')
 s=s.replace('не были частью её механизма/числовой спецификации','не описаны её механизмом/числовой спецификацией')
 s=s.replace('без переноса прежнего допуска','по текущим проверкам')
 s=s.replace('incumbent','specification')
 s=s.replace('Unchanged policy:', 'Policy:')
 s=re.sub(r'неизмен[её]нн(?:ый|ого|ому) V02','V02',s,flags=re.I)
 s=re.sub(r'неизмен[её]нного варианта','V02',s,flags=re.I)
 s=s.replace('У новых вариантов','У V01 и V04').replace('исходной V02','V02')
 return s

def neutral_md(text,alias):
 paras=[]
 for para in text.split('\n\n'):
  if 'родител' in para.lower() and (para.startswith('**CON-') or para.startswith('Родитель:') or para.startswith('От родителя') or para.startswith('От CON-')):continue
  if para.startswith('От CON-003') or para.startswith('От CON-006'):continue
  if para.startswith('| Что изменено |'):continue
  para=para.replace('Отличие от родителя —','Правила:')
  para=para.replace('Изменение к родителю, основания и условия отказа','Условия отказа и источники')
  para=para.replace('как у родителя','по указанной заявке')
  para=re.sub(r'Размер больше прежних800; это[^.]*\.', 'Расширение объёма будущих наград требует полного финансирования.',para)
  para=re.sub(r'в сравнении с v1[^.]*\.[^\n]*','Полный объём новых наград и все старые права включаются в расчёт.',para)
  para=para.replace('Что улучшено и когда отвергнуть','Условия отказа и ограничения').replace('Наследование и условия отказа','Условия отказа и ограничения')
  paras.append(para)
 text=scrub('\n\n'.join(paras))
 text=re.sub(r'(^# )[^\n]*',lambda m:m[0] if alias in m[0] else '# '+alias+' — '+m[0][2:],text,count=1,flags=re.M)
 # Drop historical ancestry/comparability paragraphs; their mechanism rules are in the main specification.
 text=re.sub(r'(?m)^От другой спецификации[^\n]*\n?','',text)
 text=text.replace('E03-E06 ABSTRACT only','E03-E06 ABSTRACT only; no causal coefficient used')
 return text+'\n'

def neutral_json(x):
 if isinstance(x,dict):
  return {scrub(k):neutral_json(v) for k,v in x.items() if k not in {'parents','parent_candidates','lineage','prior_best','selected_alias','champion','previous_rank','author','origin_path','source_snapshot','previous_input_fingerprint'}}
 if isinstance(x,list):return [neutral_json(y) for y in x]
 if isinstance(x,str):return scrub(x)
 return x

def save(path,x):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')

if __name__=='__main__':
 save(R/'private/review-map.json',{'aliases':MAP})
 (P/'candidates').mkdir(parents=True,exist_ok=True)
 for a,v in MAP.items():(P/'candidates'/f'{a}.md').write_text(neutral_md((R/v['origin_path']).read_text(),a))
 for a,f in [('V01','branches/B/policy-spec.json'),('V04','branches/A/finance-spec.json')]:save(P/'specifications'/f'{a}.json',neutral_json(json.loads((R/f).read_text())))
 for sub in ['finance','evidence']:
  src=R/'checks'/sub
  if not src.exists():continue
  for f in src.rglob('*'):
   if not f.is_file() or '__pycache__' in f.parts or f.name=='verify_versions.py':continue
   dest=P/sub/f.relative_to(src);dest.parent.mkdir(parents=True,exist_ok=True)
   if f.suffix=='.json':save(dest,neutral_json(json.loads(f.read_text())))
   elif f.suffix in {'.md','.csv','.py','.txt'}:dest.write_text(scrub(f.read_text()))
 finance=json.loads((R/'checks/finance.json').read_text());evidence=json.loads((R/'checks/evidence.json').read_text())
 save(P/'checks.json',neutral_json({'finance':finance,'evidence':evidence}))
 (P/'README.md').write_text('''# Назначенный пакет проверки\n\nЧетыре спецификации V01–V04 оцениваются по одной замороженной рубрике. Происхождение, авторство и прежние ранги не назначены reviewer.\n\nВходы: ../inputs/{context,evidence,diagnosis,baseline}.md и rubric.json; верхние дополнения C05/C06/D02/M02 имеют приоритет над сохранённым историческим текстом. Кандидаты: candidates/V01.md…V04.md; параметры: specifications/; консолидированные проверки: checks.json; расчёты и отчёты: finance/; доказательства: evidence/.\n\nЧисла сценарные, реальный бюджет/ресурсы банка не подтверждены. Финансовые pass относятся только к раскрытому scope; стрессовые отказы и неисполненные права сохраняются. Все необходимые полномочия/ресурсы должны быть проверены перед реальным пилотом. Экономия от сокращения будущих прав не эффект признания.\n\nОбезличенные программные/текстовые копии могут иметь иные хеши, чем оригиналы исполнения; manifest ниже подтверждает именно назначенные копии. Не запускайте экспортирующие model.py: проверяйте их и таблицы чтением либо отдельными формулами без изменения файлов. Запуск моделей для независимой проверки при необходимости только с изолированным временным OUT, без доступа к приватной карте/истории.\n''')
 sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
 files={str(f.relative_to(P)):sha(f) for f in P.rglob('*') if f.is_file() and f.name!='packet-manifest.json'}
 save(P/'packet-manifest.json',{'files':files})
 suspicious=[]
 for f in P.rglob('*'):
  if f.is_file() and f.suffix in {'.md','.json','.csv','.py','.txt'}:
   for pat in [r'CON-\d+@v\d+',r'branches/[AB]',r'incumbent',r'предыдущий победител',r'champion',r'review-map']:
    if re.search(pat,f.read_text(),flags=re.I):suspicious.append({'path':str(f.relative_to(P)),'pattern':pat})
 save(R/'private/packet-audit.json',{'files':len(files),'identity_patterns':suspicious,'manual_semantic_review_required':True})
 print(json.dumps({'packet_files':len(files),'audit_flags':suspicious},ensure_ascii=False))
