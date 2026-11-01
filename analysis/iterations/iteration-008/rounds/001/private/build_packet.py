"""Build a small review packet without authors, prior ranks or lineage."""
import json,re,shutil
from pathlib import Path
R=Path(__file__).resolve().parents[1]
P=R/'review-packet'
aliases={
 'V01':{'candidate_key':'CON-027@v2','kind':'candidate','origin_path':'branches/B/concept.md'},
 'V02':{'candidate_key':'BASELINE','kind':'baseline','origin_path':'inputs/baseline.md'},
 'V03':{'candidate_key':'CON-026@v2','kind':'candidate','origin_path':'branches/A/concept.md'},
 'V04':{'candidate_key':'CON-025@v1','kind':'incumbent','origin_path':'../../incumbent/concept.md'},
}
(R/'private/review-map.json').write_text(json.dumps({'aliases':aliases},ensure_ascii=False,indent=2)+'\n')
def clean(t):
 t='\n'.join(x for x in t.splitlines() if 'Независимый пересчёт A ещё требуется' not in x and not x.startswith('Родители') and not x.startswith('Parents'))
 t=re.sub(r'\[([^\]]+)\]\([^\n]*?\)',r'\1',t)
 t=re.sub(r'`[^`\n]*incumbent[^`\n]*`','общая механика и проверенная ресурсная основа',t)
 t=t.replace('setup родителя','setup общей основы').replace('родительский','базовый').replace('родителя','общей основы').replace('родитель','база').replace('этой ветки','этого способа')
 t=re.sub(r'CON-\d+(?:@v\d+)?','механика',t)
 t=re.sub(r'iteration-\d+','расчёт',t)
 t=re.sub(r'\b(?:ветка|ветки|ветке|ветку)\s+[ABАБ]\b','данный способ',t,flags=re.I)
 t=re.sub(r'\b[AB]\s*(?:v[12]|@v[12])\b','данный способ',t)
 t=re.sub(r'\b(?:parents|parent_candidates|candidate_key)\b','служебное поле',t)
 t=t.replace('механики механика','общей механики')
 return t
def remove_lineage(x):
 if isinstance(x,dict):return {k:remove_lineage(v) for k,v in x.items() if k not in ['candidate_key','parents','parent_candidates','parent','resource_parent','reward_core','money_core_reused_no_reexecution']}
 if isinstance(x,list):return [remove_lineage(v) for v in x]
 return x
(P/'candidates').mkdir(parents=True,exist_ok=True)
(P/'shared').mkdir(exist_ok=True)
core='''# Общая механика и ограничения

Одинаковые N7200/E24, ставки корпоративных событий и старые права. G2500R один раз в12месяцев за оба подходящих квартала одного фиксированного окна, без конкурсного места; первые Gm7–15. E24=18млнG+4,32млнtop+1,68млнspecialR/год, весь будущий R-блок, не сверху прежнего фонда. R→C1:1 — факт,2500C/500руб. — проектный SKU.

Поддержка и операции: принятый нормированный результат относительно независимой заранее заданной мощности, полный назначенный поток. Для проекта один целый принятый и используемый root, для аналитики один пакет для одного решения. Normal абсолютен, strong сравнивают в сопоставимых домашних пулах. QA полный, зрелый и независимый;собственные случаи отводятся,editor/signer/operator разные,source-review и отдельное точное posting-review послеclose. Исправление инвалидирует старую подпись, повтор не создаёт второй выдачи. Pending сохраняет право/окно/резерв.

Закупочный pass только M05/E24/fixed96/old20/base/34млн:31,540млн обеспечение,31,684млн с сертификатной поправкой доfees. Бюджет30млн и тяжёлые сценарии не исправлены операционными изменениями. Все численные N/остатки/частоты/ставки/часы/SKU — сценарные, не данные банка. Концептуальный проект не требует живого доступа/API/интервью, но предположения и платный резерв должны быть явными.
'''
(P/'shared/context.md').write_text(core+'\nОцените четыре псевдонима самостоятельно по rubric.json. Один — текущая программа, он не выбирается. Три проектных реализации используют общую механику. Сначала gates, затем критерии0–3 с основаниями, без обязательной суммы/победителя. Рангов и авторов в пакете нет. Можно отклонить все варианты.\n')
shutil.copyfile(R/'inputs/rubric.json',P/'shared/rubric.json')
for name in ['cards.md','employee-card.md','source-to-award.md']:
 (P/'shared'/name).write_text(clean((R.parent.parent/'incumbent'/name).read_text()))
(P/'shared/evidence.md').write_text(clean((R/'checks/evidence-for-review.md').read_text()))
for alias,item in aliases.items():
 d=P/alias; d.mkdir(exist_ok=True)
 if item['kind']=='candidate':
  src=(R/item['origin_path']).parent
  docs=['concept.md','integration-map.md','source-to-award.md','costs.md','roadmap.md','operations.csv','assumptions.csv','finance-spec.json','setup-phases.csv']
  docs += ['monthly-delta.csv','annual-delta.csv','posting-fallback.csv','summary.json','test-cases.md'] if alias=='V01' else ['manual-posting-calendar.csv','cost-summary.json','cost-periods.csv','control-tests.md']
  for name in docs:
   if (src/name).is_file():
    t=(src/name).read_text()
    if name.endswith('.json'):t=json.dumps(remove_lineage(json.loads(t)),ensure_ascii=False,indent=2)
    (d/name).write_text(clean(t))
  intro=f'# {alias}: способ внедрения\n\n'+core+'\n'+clean((src/'concept.md').read_text())
 elif item['kind']=='baseline':
  intro=f'''# {alias}: действующая программа

HR администрирует портал и корпоративные начисленияC. Руководитель поощряет конкретный вклад из квартального фондаR. Есть кошельки,магазин,конвертацияR→C1:1,личные остатки не сгорают; невыданный квартальный фонд обнуляется. Руководителя может поощрить вышестоящий. Обычный сотрудник не имеет описанной гарантии за два качественных квартала.

ФондQ3 38,540млнR,выдано19,427591млн,невыдано19,112409млн. Это не покупки и не факт годовой эмиссии. Стоимость текущего труда/подробная матрица доступа неизвестны и не равны нулю. В сравнении денежных границE24 используется только аналитический предел,не приписывается действующему банку. Нельзя автоматически объявить текущую программу проходящей бюджет/gates при неизвестном реальном годе и остатках.

Источники: PDFс.9–19; Transcript39:55,43:03,50:26;wiki/case/program-rules.md,platform-and-administration.md,catalog-and-operations.md.
'''
 else:
  src=R.parent.parent/'incumbent'
  for name in ['cards.md','employee-card.md','source-to-award.md']:
   (d/name).write_text(clean((src/name).read_text()))
  intro=f'''# {alias}: ролевой результат с заранее оплаченным помесячным календарём

{core}

Работник продолжает обычную работу,готовые источники предполагаются. Расчёт/источник/независимое разрешение/проводка различаются. Обязательные личные4мин и недостающийQA5мин/инспекцию учтены. Все7200подходящих,полныеG/top/special,старый/fixed/new магазин и обращения входят в заранее подписанный39месячный календарь. Спрос не уменьшается по фактическому U или отсутствию подписи.

Setup3,990млнруб. Bookings19,320млн за39месяцев вEXPECTED/fixed96/QA100/×1/замещение0,по периодам2,970/7,260/7,260/1,830млн. HRбаза220ч/мес,блоки20чдоHR6,ownerQA240,employee4,IT3;ставки1000/1500/1000/2000руб./ч. СуществующийQA2436ч/мес отдельно. Полная стоимость деятельности+простой150,531467млнруб.39месяцев,включая существующий труд,не целиком дополнительные деньги.

Календарь заранее конечен,без бесплатногоstandby;люди/контракт/финансирование и подмесячные пики неизвестны. При×2/JANfixed144 отрицательные результаты сохранены. Данная реализация описывает обобщённую цепочку авторизации,но адресный физический ввод в существующий admin и отдельный отказной построчный резерв не детализированы новыми действиями. Не дополняйте её функциями других вариантов задним числом.

Ролевые карточки,личный путь и source-to-award в соседних файлах являются содержанием этой неизменённой реализации. Зафиксированная точная копия проверена независимо;пакет убирает происхождение,не меняет механику.
'''
 (P/'candidates'/f'{alias}.md').write_text(intro)
fin=json.loads((R/'checks/finance.json').read_text())
evi=json.loads((R/'checks/evidence.json').read_text())
rev={v['candidate_key']:k for k,v in aliases.items()}
def blind(rows):
 result=[]
 for x in rows:
  q={k:v for k,v in x.items() if k not in ['candidate_key','calculation_paths','evidence_refs','assumption_refs']}
  q['alias']=rev[x['candidate_key']]
  result.append(json.loads(clean(json.dumps(q,ensure_ascii=False))))
 return result
(P/'checks.json').write_text(json.dumps({'finance':blind(fin['results']),'evidence':blind(evi['results'])},ensure_ascii=False,indent=2)+'\n')
(P/'shared/finance.md').write_text(clean((R/'checks/finance-for-review.md').read_text()))
(P/'README.md').write_text('# Назначенный пакет reviewer\n\nСначала shared/context.md,rubric.json,evidence.md,finance.md,cards.md,employee-card.md,source-to-award.md и checks.json. Затем candidates/V01…V04.md и соответствующие supporting папки V01/V03/V04. Оцените все gates/criteria и допустимый shortlist. Не открывайте private,branches,incumbent,selection или историю запусков. Первичные материалы кейса и wiki доступны по необходимости.\n')
for f in P.rglob('*'):
 if f.is_file():
  t=f.read_text()
  assert not re.search(r'CON-\d+|iteration-\d+|review-map|selected_alias|champion',t),f
print('Blinded packet built:',len([f for f in P.rglob('*') if f.is_file()]),'files')
