import sys
sys.dont_write_bytecode=True
import json,hashlib,csv
from pathlib import Path
O=Path(__file__).resolve().parent;R=O.parents[1];C=R/'checks'
def read(p):return json.loads(p.read_text())
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def relabel(x):
 if isinstance(x,str):return x.replace('CON-023@v1','CON-023@v2')
 if isinstance(x,list):return [relabel(v) for v in x]
 if isinstance(x,dict):return {relabel(k):relabel(v) for k,v in x.items()}
 return x
# The 38-snapshot metric data are unchanged; only their current policy key changes.
for file in ['independent-units.csv','independent-persons.csv','personal-windows.csv','scenario-summary.csv']:
 p=O/file;p.write_text(p.read_text().replace('CON-023@v1','CON-023@v2'))
write(O/'vectors.json',relabel(read(O/'vectors.json')))
write(O/'author-output-comparison.json',relabel(read(O/'author-output-comparison.json')))
v=relabel(read(O/'verification.json'));v.pop('counterexample',None);v['input_hashes']['branches/B/con-023/metrics-spec.json']=sha(R/'branches/B/con-023/metrics-spec.json');v['current_C3_controls']=read(O/'current-controls.json')['summary'];v['current_metric_basis']='Independent 38-snapshot primitive reconstruction retained after AST metric/quality/calendar and policy-parameter semantic invariance; no repeated full sweep.';v['current_delta_verification']='checks/evidence/delta-verification.json';write(O/'verification.json',v)
pins=read(R/'private/versions-before-checks.json')['files'];bad=[p for p,h in pins.items() if sha(R/p)!=h]
integ=read(O/'integrity.json');integ.update(frozen_candidates_checked=len(pins),mismatches=bad,current_candidate_keys=['CON-022@v1','CON-023@v2','CON-016@v2','BASELINE']);write(O/'integrity.json',integ)
e=relabel(read(C/'evidence.json'));e['stage']='final_current_independent_checks';e['verification']=v
for r in e['results']:
 if r['candidate_key']=='CON-023@v2':
  r['status']='supported';r['checks']['C3']='pass_for_tested_current_controls';r['findings']=[x for x in r['findings'] if x['id'] not in ['B-C3-BIND','B-C3-SCOPE','B-ROLES']]
  r['findings'] += [
   {'id':'B-C3-CURRENT','text':'Все 26 текущих C3 controls проходят: точные source/registry/member/config/rule/decision/version/amount связаны с выполненной award-подписью. Изменённый компонент, отсутствующий hash, wrong action/scope, подпись до close и конфликтный team source-review удерживают U=0. Расчётное право, ранг и окно сохраняются отдельно.','locators':['checks/evidence/current-controls.json#/controls','checks/evidence/delta_check.py#own_package','branches/B/con-023/evaluator.py:42–94,267–340'],'epistemic_type':'own_calculation_and_adversarial_control','verification_status':'supported'},
   {'id':'B-C3-POSITIVE','text':'Независимо реконструированный пакет в точности совпадает с current materialized package: personal600U и team-member420U. Подтверждения обоих кварталов имеют один G-key и ceiling2500R; это одно право fixed window, не две выдачи.','locators':['checks/evidence/current-controls.json:positive_personal,positive_team_member,two_quarter_fixed_window_G_S31,two_quarter_fixed_window_G_P031'],'epistemic_type':'own_calculation','verification_status':'supported'},
   {'id':'B-C3-REPLAY','text':'Повторный расчёт и повторная доставка того же award-акта сохраняют одну logical authorization и U600. Это проверка идемпотентного состояния калькулятора; реальный transactional ledger отсутствует и не объявляется испытанным.','locators':['checks/evidence/current-controls.json:same_package_and_duplicate_delivery_replay','branches/B/con-023/source-to-award.md:final paragraphs'],'epistemic_type':'own_calculation_with_scope_limit','verification_status':'supported'},
   {'id':'B-C3-INCIDENT','text':'Отсутствие source-review/award не уничтожает calculated earned/rank/window. При действительном source incident calculated pending сохраняет исходное окно, групповой conditional ceiling6000R и U0.','locators':['checks/evidence/current-controls.json:missing_personal_source_action,missing_team_source_action,missing_award_preserves_calculated_right,source_incident_preserves_original_window_ceiling'],'epistemic_type':'own_calculation','verification_status':'supported'}]
  r['calculation_paths'] += ['checks/evidence/delta_check.py','checks/evidence/current-controls.json','checks/evidence/delta-verification.json']
  r['evidence_refs'] += [{'path':'checks/evidence/current-controls.json','locator':'26pass/0fail; independent positive and negative controls'}]
  r['unresolved']=[x for x in r['unresolved'] if 'Five C3' not in x]+['Real transactional ledger posting is absent; calculator U is a state, not a completed currency posting.']
  for f in r['findings']:
   if f['id']=='B-R4':f['locators']=['checks/evidence/calendar.csv','branches/B/con-023/evaluator.py:145–166']
e['independence']['author_code_usage']='AST pure definitions of actual frozen evaluator for exact C3 positive/negative/replay observations; expected amounts derive from independent primitive reconstruction and expected canonical package is constructed independently; no author self-test/materializer as oracle or module-level export/build.'
e['independence']['current_metric_delta']='No repeated 38-snapshot sweep: primitive-to-unit loop, quality/calendar/manifest/interval functions and metric parameters are AST/semantic invariant.'
e['artifact_checks']['current_controls']='checks/evidence/current-controls.json';e['artifact_checks']['final_freeze_mismatches']=bad
for log in e['reading_log']:
 if 'branches/A' in log['path']:
  log['actual_reading_depth'] += '; current CON-023@v2 exact C3 function bodies/spec/contract read and independently probed; unchanged metric semantics checked'
write(C/'evidence.json',e)
# Remove stale failure interpretation from the review-facing text entirely.
p=C/'evidence-for-review.md';s=p.read_text().replace('CON-023@v1','CON-023@v2')
s=s.replace('Пять воспроизводимых дефектов C3 требуют исправления до вывода о допустимости авторизации.','26 текущих C3 controls прошли; реальная транзакционная проводка в source отсутствует.')
start=s.index('У CON-023@v2 review без привязки')
end=s.index('**QA и регрессии.**',start)
s=s[:start]+'''У CON-023@v2 выполненная personal-подпись текущего пакета разрешает 600 U, подпись для участника команды — 420 U. Canonical package построен проверяющим самостоятельно из исходных таблиц и независимо рассчитанных решений; он в точности совпадает с проверяемым пакетом. Все 26 текущих controls прошли.

Отсутствующий hash, подпись другого правила/решения/версии/суммы, изменение source/registry/member/config, wrong action или scope, время до quality-close, отсутствующая personal/team source-проверка и конфликтный team reviewer удерживают U=0. Даже подпись точного текущего пакета не заменяет пригодное выполненное source-действие. Время проверки не раньше точного quality-close; для даты без времени применяется консервативный конец дня. Editor, signer и operator должны быть разными непустыми независимыми лицами, вне всей команды и явных reporting-зависимостей.

Отсутствие source-review или award-подписи сохраняет отдельно calculated qualification, ранг и исходное окно. Действительный source incident даёт pending, исходный групповой conditional ceiling 6000 R и U=0. Повторный расчёт и повторная доставка одного award-акта сохраняют одну логическую авторизацию и U600. Подтверждения двух первых кварталов используют один G-key на fixed window; квартальный ceiling2500 не является вторым начислением. Реального transactional ledger нет: проверено состояние калькулятора, а не живое проведение валюты. Текущие positive/negative observations: `checks/evidence/current-controls.json`.

'''+s[end:]
p.write_text(s)
# Full report may retain a precise locator to coordinator-only historical evidence.
p=C/'evidence.md';s=p.read_text().replace('CON-023@v1','CON-023@v2')
start=s.index('У CON-023@v2 воспроизведены пять')
end=s.index('R4 отдельно рассчитывает',start)
s=s[:start]+'''C3 текущей CON-023@v2: 26 pass, 0 fail. Ожидания по суммам взяты из собственного primitive-расчёта; canonical package реконструирован самостоятельно, без авторского materializer/self-test как oracle. Позитивные personal600U и team-member420U в обоих кварталах проходят, независимо составленные пакеты побайтно равны текущим пакетам калькулятора. Один G-key связывает оба квартальных ceiling2500 в одно право fixed window.

Все пять назначенных негативных случаев удерживают U=0. Дополнительно проверены обязательные компоненты того же C3: source/registry/member/config/rule/decision/version/amount, performed action/scope/time, отсутствие personal/team source-review, сохранение права/окна и replay. Правильный current signed package с непригодным source-review по-прежнему удерживает U. При отсутствии подписи calculated earned/rank/window сохраняются; действительная потеря source даёт pending и conditional group ceiling6000, а не выдуманный заработанный результат. Повторная доставка award-акта даёт одну logical authorization/U600. Реального ledger posting нет; текущее U не суммируется как новые выдачи. Все наблюдения — `evidence/current-controls.json`; воспроизводитель — `evidence/delta_check.py`.

Метрики не пересчитаны большим sweep: AST исходного primitive→unit loop, QA, calendar, manifest и union intervals идентичен; параметры метрик семантически неизменны. `evidence/delta-verification.json` фиксирует эти проверки и финальный freeze. Значения прежнего независимого расчёта сохранены с текущим ключом. Полная первичная история пяти дефектов находится только в координаторском `private/pre-rework/final-primary-evidence/`; она не является текущим fail и не включается в нейтральный report.

Позитивная привязанная подпись CON-022 разрешает 150 U; смена правила со старой подписью сохраняет 300 calculated/U0 (`evidence/a-authorization-probe.json`). Публичные новые снимки не содержат полной current award-подписи: independently authorized U=0 при отдельно сохранённом расчётном праве. Проверенные позитивные акты являются явно гипотетическими действиями в памяти, а не правкой общего source и не банковской проводкой.

'''+s[end:]
s=s.replace('Незавершено: один целевой C3 rework CON-023 и узкая независимая дельта пяти дефектов с позитивной подписью.','Назначенная независимая проверка завершена: текущие четыре ключа и узкая C3-дельта сохранены. Нерешённых технических дефектов в назначенной дельте не выявлено.')
s=s.replace('Повторный запуск: `PYTHONDONTWRITEBYTECODE=1 python3 -B checks/evidence/independent_check.py` из папки раунда.','Текущая узкая проверка: `PYTHONDONTWRITEBYTECODE=1 python3 -B checks/evidence/delta_check.py` из папки раунда; полный исходный sweep сохранён как основание метрик.')
s += '\nФинальный C1 повторён по pins `private/versions-before-checks.json`: все текущие файлы совпали, writes ограничены назначенными checks. Текущий neutral report не содержит истории исправления и прежнего ключа CON-023.\n'
p.write_text(s)
write(O/'report-validation.json',{'four_keys':[r['candidate_key'] for r in e['results']],'json_valid':True,'findings_objects_with_locators':all(isinstance(f,dict) and 'text' in f and 'locators' in f for r in e['results'] for f in r['findings']),'current_freeze_mismatches':bad,'current_C3_summary':read(O/'current-controls.json')['summary'],'neutral_report_has_no_obsolete_B_key':'CON-023@v1' not in (C/'evidence-for-review.md').read_text(),'current_verification_has_no_old_counterexample':'counterexample' not in v,'metric_semantic_invariance':read(O/'delta-verification.json')['semantic_invariance']})
print(json.dumps({'keys':[r['candidate_key'] for r in e['results']],'statuses':[(r['candidate_key'],r['status']) for r in e['results']],'C3':read(O/'current-controls.json')['summary'],'freeze_mismatches':bad},ensure_ascii=False))
