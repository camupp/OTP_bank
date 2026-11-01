#!/usr/bin/env python3
"""One authorized targeted rework: actual nonempty signature time. Do not rerun after freeze."""
from pathlib import Path
import csv,hashlib,json
HERE=Path(__file__).resolve().parent
BRANCH=HERE.parent
ROUND=HERE.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for num in [18,19]:
 p=BRANCH/f'con-{num:03d}';key=f'CON-{num:03d}@v2';prev=f'CON-{num:03d}@v1'
 before={'candidate_key':key,'parents':[prev],'classification':'v1 comparison evidence, not a second candidate','files_sha256':{x.name:sha(x) for x in p.iterdir() if x.is_file() and x.name not in ['rework_v2.py']},'metrics_spec':json.loads((p/'metrics-spec.json').read_text()),'decisions':list(csv.DictReader((p/'decisions.csv').open())),'money':list(csv.DictReader((p/'money-examples.csv').open()))}
 (p/'rework-baseline.json').write_text(json.dumps(before,ensure_ascii=False,indent=2)+'\n')
 q=p/'evaluator.py';s=q.read_text();old="    return 'signed',a['approval_id']\n";new="    signed_at=a.get('signed_at')\n    if not isinstance(signed_at,str) or not signed_at.strip():\n        return 'missing_signature_time',a['approval_id']\n    return 'signed',a['approval_id']\n"
 assert s.count(old)==1;s=s.replace(old,new)
 s=s.replace("'capacity_fields':capacity,", "'capacity_fields':capacity,'approval_evidence':[a for a in data['approvals_audit'] if a['period_id']==p and a['beneficiary_id'] in excluded],")
 s=s.replace("dict(scenario=name,**r)","dict(candidate_key=spec['candidate_key'],scenario=name,**r)")
 s=s.replace("dict(scenario=name,**d)","dict(candidate_key=spec['candidate_key'],scenario=name,**d)")
 q.write_text(s)
 q=p/'metrics-spec.json';o=json.loads(q.read_text());o['candidate_key']=key;o['rule_version']=f'A{num}-prospective-2';o['signing']['actual_signature_time']='status signed requires a factual signed_at string that is not empty or whitespace, in addition to the unchanged independent roles/control-chain checks. Named actors without timestamp are not a completed signature.';o['signing']['missing_signature']='missing_signature_time holds posting/approvedU; computed normal, eligibility, calculated G/top and original window/date remain. No inferred timestamp from named signer, role assignment or alternate.';q.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n')
 q=p/'finance-spec.json';o=json.loads(q.read_text());o['candidate_key']=key;o['operational_metrics_assumptions']=json.loads((p/'metrics-spec.json').read_text());o['signature_performance_requirement']='Independent roles plus actual nonempty signed_at; absent signature time => held, approvedU0, original earned/calculated right retained; no changes to funds/rates/windows/resource.';o['HR_peak_interpretation']={'source':'../../../checks/finance.md','upper_bound_hours':320.93333333333334,'upper_bound_scope':'conservative sum of separately maximized common shop and award/small-SKU workloads, not exact simultaneous EXPECTED peak','exact_simultaneous_E24_from_independent_finance_hours':{'EXPECTED':231.38,'FULL_NEW':248.44,'JAN_OLD50':319.41},'HR_limit_unchanged':220,'admission':'no HR220 pass claimed; no labor minutes/resources changed'};q.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n')
 for name in ['cards.md','employee-card.md','source-to-award.md','README.md']:
  q=p/name;s=q.read_text();s+='\n**Фактически выполненная подпись.** Одних назначенных независимых ролей недостаточно. В `approvals_audit.signed_at` должна быть непустая дата/время фактической подписи (не пустая строка или пробелы). Если её нет, статус — `missing_signature_time`: проводка и подтверждённое U удержаны. Измеренный normal, расчётная гарантия/top, исходное окно и дата доказанного права сохраняются; время подписи не подставляется из других полей.\n';q.write_text(s)
 q=p/'concept.md';s=q.read_text();s=s.replace('Никто не утверждает собственные входы/тип/исключение/приёмку/QA/апелляцию/ставку/проводку.', 'Никто не утверждает собственные входы/тип/исключение/приёмку/QA/апелляцию/ставку/проводку. Подтверждение подписи требует фактического непустого `signed_at`; одних назначенных независимых ролей недостаточно. Без даты проводка и подтверждённое U удержаны, расчётное/заработанное право и исходное окно не уничтожаются.')
 s+='\nУточнение пиков HR по независимому [финансовому расчёту](../../../checks/finance.md): 320,93 ч — консервативная сумма отдельно максимизированных нагрузок, а не точный одновременный EXPECTED-пик. Точные одновременные пики E24: EXPECTED 231,38 ч; FULL_NEW 248,44 ч; JAN_OLD50 319,41 ч. Они всё равно превышают 220 ч. Собственные минуты и ресурс не изменены; HR220 pass не заявлен.\n';q.write_text(s)
 # No metric, award, calendar or labor assumption is replaced.
 q=p/'assumptions.csv';rows=list(csv.DictReader(q.open()))
 for r in rows:
  if r['id']=='A17':r['value']='hold posting without actual nonempty signed_at';r['limitation']='Independent named roles and alternate are not factual performance. Calculated right/window remains, approvedU0 until signature.'
 with q.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 q=p/'changes.md';q.write_text(f'''# Lineage и единственный целевой rework

- Текущая версия: `{key}`; parents: `[{prev}]`; ветка A.
- v1 побайтно сохранена координатором в архиве до rework; архив этим исполнителем не читался и не изменялся.
- Основание: `checks/evidence/counterexamples.json`, только запись `SIG-A-NO-TIME`. Копия source меняет `approvals_audit#P1:S01.signed_at` на null при сохранённых независимых ролях. Старый предикат возвращал signed без факта времени.

**Точный diff механики:** после прежних проверок независимых editor/signer/operator/appeal и зависимостей `signoff` требует строковый `signed_at`, непустой после strip. При отсутствии, null, пустой строке или пробелах возвращает `missing_signature_time`. Проводка held, подтверждённые U не создаются; eligibility/normal, расчётные G/top и исходное окно/дата сохраняются. Иных изменений метрики, наград, норм, окон и ресурсов нет. Проектный root-норматив018 остаётся отсутствующим.

Спецификация, карточки и код согласованы. Пересчитаны прежние base+22 варианта. В outputs добавлен текущий candidate_key и обновлён rule_version; trace дополнен доступной подписью из source. Сравнение содержательных результатов v1/v2 и полный проверочный контрпример сохраняются в `rework-comparison.json` и `signature-counterexample.json`; локальные проверки — `self-check.json`.

Денежные инварианты, пины M05/006 и источник сохраняются. Уточнение HR по `checks/finance.md`: 320,93 ч — консервативная сумма максимумов; точные одновременные E24 EXPECTED/FULL_NEW/JAN_OLD50 пики 231,38/248,44/319,41 ч. Минуты/ресурс не подгонялись, HR220 pass не заявлен. Независимый допуск этим rework не присваивается.
''')
# Keep optional old document-build helpers from emitting obsolete current keys. Not executed.
for name in ['build_artifacts.py']:
 q=HERE/name;s=q.read_text().replace("f'CON-{num:03d}@v1'","f'CON-{num:03d}@v2'").replace("f'A{num}-prospective-1'","f'A{num}-prospective-2'")
 s=s.replace('candidate_key:CON-{num:03d}@v1;parents:[CON-016@v2];branch:A.','candidate_key:CON-{num:03d}@v2;parents:[CON-{num:03d}@v1];branch:A.')
 q.write_text(s)
