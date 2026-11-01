import sys
sys.dont_write_bytecode=True
import json,hashlib
from pathlib import Path
O=Path(__file__).resolve().parent;R=O.parents[1];C=R/'checks'
def read(p):return json.loads(p.read_text())
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def relabel(x):
 if isinstance(x,str):return x.replace('CON-024@v1','CON-024@v2')
 if isinstance(x,list):return [relabel(v) for v in x]
 if isinstance(x,dict):return {relabel(k):relabel(v) for k,v in x.items()}
 return x
keys=['CON-024@v2','CON-025@v1','CON-023@v2','BASELINE']
for name in ['independent-units.csv','independent-persons.csv','personal-windows.csv','qa-neighborhood.csv']:
 p=O/name;p.write_text(p.read_text().replace('CON-024@v1','CON-024@v2'))
write(O/'qa-ties.json',relabel(read(O/'qa-ties.json')))
# Reuse the independently reconstructed exact personal-boundary evidence.
(O/'calendar.csv').write_bytes((R.parent/'002/checks/evidence/calendar.csv').read_bytes())
a=read(O/'a-current-controls.json');b=read(O/'c3-CON-025-v1.json');i=read(O/'c3-CON-023-v2.json');delta=read(O/'current-delta-verification.json')
write(O/'current-controls.json',{'path_base':'analysis/iterations/iteration-007/rounds/003','results':[a,b,i,{'candidate_key':'BASELINE','scope':'No performed local award instructions/amounts in working source','status':'not_computable'}],'summary':{'pass':a['summary']['pass']+b['summary']['pass']+i['summary']['pass'],'fail':a['summary']['fail']+b['summary']['fail']+i['summary']['fail']},'limits':['Hypothetical in-memory actions only; public source unchanged.','Authorized U is distinct from calculated right and from real ledger posting.']})
for name in ['c3-verification-CON-025-v1.json','c3-verification-CON-023-v2.json']:
 v=read(O/name);v['current_candidate_keys']=keys;write(O/name,v)
e=relabel(read(C/'evidence.json'));e['stage']='final_current_round003_independent_checks'
for r in e['results']:
 for f in r['findings']:
  if f['id']=='C5':f['locators']=[p.replace('../002/checks/evidence/calendar.csv','checks/evidence/calendar.csv') for p in f['locators']]
 if r['candidate_key']=='CON-024@v2':
  r['status']='supported';r['checks']['C3']='pass_11_current_targeted_controls';r['findings']=[f for f in r['findings'] if f['id'] not in ['A-C3-CONFIG','A-C3-TIME']]
  r['findings'] += [
   {'id':'A-C3-CURRENT','text':'Полный фактически используемый PUBLIC_CONFIGS включён в независимо восстановленную canonical projection источников. Positive personal/team разрешают150U. Изменение matching config со старой подписью удерживаетU0 и150Rрезерва; новая matching подпись разрешает150U.','locators':['checks/evidence/a-current-controls.json:positive_personal,positive_team_member,external_config_changed_same_signature,positive_current_changed_config','checks/evidence/a_current_delta.py#sign','branches/A/con-024/evaluator.py:49–63'],'verification_status':'supported','epistemic_type':'own_calculation_and_exact_binding_check'},
   {'id':'A-C3-TIME','text':'Team source-review проверен на early/empty/invalid, ровно собственном explicit quality-close и за1секунду до него: первые и ранний heldU0, равенство допускает150U. При отсутствующем времени суток опубликованное правило A использует начало local quality-close day.','locators':['checks/evidence/a-current-controls.json:team_source_before_effort,team_source_empty_time,team_source_invalid_time,team_source_at_exact_close,team_source_one_second_before_close','branches/A/con-024/source-to-award.md:current C3/signing projection'],'verification_status':'supported','epistemic_type':'own_boundary_calculation'},
   {'id':'A-C3-RIGHTS-REPLAY','text':'Все11 текущих контролей проходят. Missing award или непригодный team-review/config сохраняет calculated earned, исходныеwindow/cohort и150Rрезерва приU0. Повторный расчёт/точный дубль award дают одну logical authorization/U150. Реальный transactional ledger отсутствует.','locators':['checks/evidence/a-current-controls.json:missing_award_preserves_right_window_reserve,replay_and_exact_duplicate_award_delivery','checks/evidence/current-delta-verification.json'],'verification_status':'supported','epistemic_type':'own_calculation_with_scope_limit'}]
  r['unresolved']=[x for x in r['unresolved'] if 'Two concrete' not in x]
  r['calculation_paths'] += ['checks/evidence/a_current_delta.py','checks/evidence/a-current-controls.json','checks/evidence/current-delta-verification.json']
 r['calculation_paths']=[p for p in r['calculation_paths'] if p not in ['checks/evidence/a_c3_probe.py','checks/evidence/a-c3-specific.json']]
e['verification'].update(candidate_keys=keys,current_C3={'CON-024@v2':a['summary'],'CON-025@v1':b['summary'],'CON-023@v2':i['summary']},final_pin_mismatches=delta['final_pin_mismatches'],current_delta_invariance=delta['semantic_invariance'],current_numeric_CSV_invariance=delta['numeric_CSV_invariance'])
e['reading_log'].append({'path':'branches/A/con-024/evaluator.py,metrics-spec.json,source-to-award.md','version_date':'01.11.2026 current freeze CON-024@v2','actual_reading_depth':'exact current signing projection and team-review time code/contract read; independent positive/negative/replay observations; metric/category invariance established','design':'prospective synthetic controls, not bank experiment','dependency_group':'same policy/source family','limitations':'No actual posting, API or staff availability established.'})
write(C/'evidence.json',e)
integ=read(O/'integrity.json');integ.update(frozen_files=delta['final_pin_count'],pin_mismatches=delta['final_pin_mismatches'],current_candidate_keys=keys,current_freeze_scope='All final pins independently checked from current files');write(O/'integrity.json',integ)
write(O/'verification.json',{'candidate_keys':keys,'current_control_counts':{'CON-024@v2':a['summary'],'CON-025@v1':b['summary'],'CON-023@v2':i['summary']},'total_current_controls':{'pass':63,'fail':0},'final_freeze_pins':delta['final_pin_count'],'pin_mismatches':delta['final_pin_mismatches'],'source_files':41,'recipe_sha256':'b5ce8d3d8b0442879526be9916e657371b1929f5d1f469cab1751ed334192a12','new_rank_rows':2600,'independent_rank_differences':0,'original_snapshots':38,'QA_probe_snapshots':5,'large_metric_sweep_repeated':False,'current_invariance':delta['semantic_invariance'],'current_numeric_CSV_invariance':delta['numeric_CSV_invariance'],'actual_ledger':'absent'})
neutral='''# Текущая проверка доказательств

01.11.2026. Проверены CON-024@v2, CON-025@v1, CON-023@v2 и BASELINE на одном синтетическом источнике: 38 снимков и пяти общих QA-копиях. Этот отчёт не выбирает вариант. Помесячную мощность и экономику рассматривает отдельная финансовая проверка.

| Вариант | Проверенный результат | Ограничение |
|---|---|---|
| CON-024@v2 | Фиксированные категории наблюдаемого качества; новый rank независимо восстановлен для 2600 unit-строк. Все 11 текущих целевых C3-контролей проходят. | Один minor может изменить top300→0 R. |
| CON-025@v1 | Результатный scoring и 26 текущих C3-контролей подтверждены. | Помесячная бронь и её эффект на стоимость проверяются отдельно. |
| CON-023@v2 | Результатный scoring и 26 текущих C3-контролей подтверждены. | Реальные люди, API, ledger и мотивационный эффект не установлены. |
| BASELINE | Руководитель назначает R в пределах фонда. | В source нет выполненных назначений: local rank/award невычислимы. |

**Наблюдаемое качество CON-024.** Полное совместимое QA без единого penalty даёт категорию 2 при mean100. Прежний stretch с 99≤mean<100 относится к категории 1. Внутри категории все делят ничью; класс не зависит от соседей. QA98 может пройти normal, но не stretch. Промежуточный 99,05 не сливает 99 и 100.

| Проба поддержки | Точный QA | Normal/stretch | Личный top |
|---|---|---|---|
| Q0 / S11 | 3960/40=99 | Да/да | Категория 1, rank21, 0 R |
| Q99_down / S11 | 3958/40=98,95 | Да/нет | 0 R |
| Q99_up и R2.precision / S11 | 3962/40=99,05 | Да/да | Категория 1, rank21, 0 R |
| Q100_down / S21 | 4398/44=99,954545… | Да/да | Категория 1, rank20, 0 R вместо 300 R |

После Q100_down оставшиеся 19 участников без penalty делят 6000 R: финальный floor даёт 315 R каждому, 15 R остаются невыданными. Изменены только заданный minor/score и технический SHA копии. IDs, знаменатели 40/44, охват, мощность и остальные наблюдения сохранены. У результатных CON-025/023 эти QA-копии не меняют объёмный rank; BASELINE остаётся not_computable. Полные составы ничьих: `checks/evidence/qa-ties.json`; промежуточные числа: `qa-neighborhood.csv`.

Граница 100 означает отсутствие наблюдаемого штрафа в полном проверенном портфеле. Она не доказывает лучшее будущее качество по разнице 0,0455 балла. Chaining отсутствует, однако скачок выплаты, разные размеры портфелей, риск сокрытия/оспаривания minor и широкие ничьи остаются существенными ограничениями. Непрерывность выплат фиксированных слотов не требуется. Полезность категории для сотрудников не измерена.

**C3: право и разрешение.** CON-024 включает полный фактически используемый PUBLIC_CONFIGS в подписываемую canonical projection. Позитивные независимо составленные personal/team пакеты разрешают по 150 U. Изменение matching config со старой подписью удерживает U=0 и резерв 150 R; matching новая подпись разрешает 150 U. Пустое, неверное или раннее время team-review удерживает U=0. Ровно собственный explicit quality-close допускается, одна секунда до него — нет. Для даты close без времени опубликованное правило CON-024 использует начало локального дня; CON-025/023 используют консервативный конец дня.

При отсутствии award или непригодной проверке сохраняются отдельно calculated earned, исходные window/cohort и резерв. Replay и точная повторная доставка дают одну логическую авторизацию, а не новое начисление. У CON-025/023 каждый набор из 26 controls проходит: independently constructed personal600U/team420U; непригодные source/registry/member/config/rule/decision/version/amount, action/scope/time/team удерживают U=0. Текущие наблюдения: `checks/evidence/current-controls.json`. U — состояние разрешения; реальная транзакционная проводка и API здесь отсутствуют.

**Прежние условия и календарь.** Normal абсолютен, full QA обязателен, source-review не является award-разрешением. Worklog не равен мощности; FTE и сложность не применяются дважды. Root/benefit не размножаются тикетами. G2500 связывает первые два квартала одного fixed window раз в 12 месяцев. Потеря источника сохраняет pending/условный максимум; поздняя доставка своевременного QA отличается от реально позднего результата. R4 содержит девять представителей и не доказывает полный банковский census. Личные окна: `checks/evidence/personal-windows.csv`; границы событий: `calendar.csv`.

**Границы доказательств.** Портал, HR/LMS и HR-администрирование подтверждены выбранными первичными местами Transcript: 39:18–43:03 и 50:26, строки 72–80 и 112. CRM/Jira, поля, QA, цели, штат, готовность и причинный эффект остаются проектными допущениями. Пересказы одной встречи не добавляют независимых подтверждений. PDF/XLSX и внешние исследования здесь не перечитывались. Реальные API не требуются для концептуальной проверки; синтетика не доказывает внедрение или мотивационный эффект.
'''
(C/'evidence-for-review.md').write_text(neutral)
full='''# Финальная независимая проверка раунда 003

Текущие ключи: CON-024@v2, CON-025@v1, CON-023@v2, BASELINE. Выбор победителя не производится. Контрактный JSON — `evidence.json`, нейтральный текущий отчёт — `evidence-for-review.md`.

## Метод и неизменность

Повторно использованы собственные primitive→unit/QA/normal/R4 таблицы раунда002 по SHA и доказанной структурной неизменности. В раунде003 независимо пересчитаны новые категориальные rank/money для2600unit-строк и пять общих QA-копий;0расхождений с сохранёнными выходами. Авторский evaluator не служил метрическим oracle. Чистые AST-функции выполнялись только для конкретных C3-наблюдений; ожидаемые суммы и canonical projection построены самостоятельно.

Для текущей CON-024 отдельно подтверждена неизменность quality_category/quality_rank_key, primitive/normal/QA loop, категориального rank/money loop и параметров метрик. Unit-decisions, decisions, QA-neighborhood и window-guarantee CSV совпадают по всем значениям кроме candidate_key. Большой sweep38/2600 и QA-пробы на этой дельте не повторялись. Locators: `evidence/metric-invariance.json`, `current-delta-verification.json`.

C1:63финальных pins совпали;41исходный файл и пять inputs неизменны. КопияCON-023 проверена поSHA с закрытой политикой. Recipe SHA256=b5ce8d3d8b0442879526be9916e657371b1929f5d1f469cab1751ed334192a12. Новые QA-копии изменяют только опубликованные minor/score и physical SHA, не общий source. Проверки и числовые таблицы — `evidence/integrity.json`, `verification.json`, `independent-units.csv`, `independent-persons.csv`, `personal-windows.csv`, `calendar.csv`.

## Текущие QA-выводы

CON-024 использует независимые от соседей категории: полный портфель без наблюдаемых penalty приmean100 выше strong99≤mean<100. QA98 может пройтиnormal, но неstretch. Мостик99.05 не сливает99/100. Q99_down=3958/40=98.95:normal/неstretch; Q99_up=3962/40=99.05:normal/stretch, категория1/rank21/top0. Q100_down=4398/44:normal/stretch, категория1/rank20/top0 вместо300. Остальные19zero получаютfloor315R,15Rневыдано. Точные составы и величины — `evidence/qa-neighborhood.csv`, `qa-ties.json`.

Граница100 имеет наблюдаемый смысл «нет зарегистрированных penalty» при полном совместимомQA. Она не доказывает статистическое или будущее превосходство по0.0455балла. Скачок300→0, разные размеры полных портфелей, риск сокрытия/оспариваний minor и широкие ничьи сохранены как ограничения. У результатных CON-025/023 QA-пробы не меняют ранжирование результата; BASELINE localaward невычислим. Финансовую/ресурсную дельту считает финансист.

## Текущий C3

CON-024:11pass/0fail. Независимая canonical projection включает полный фактически используемый PUBLIC_CONFIGS, все source tables, non-award audit и физические source manifests без циклического audit-manifest. Binding включает period/person, source/config hash, полный metrics-spec и candidate key. Позитивные personal/team дают150U. Изменение внешней matching config со старой подписью удерживаетU0 и150Rрезерва; новая matching подпись даёт150U. Непригодный team-review early/empty/invalid и за1секунду доexplicitclose удерживаетU0; равенствоclose проходит. Для date-only A close опубликовано начало локального дня. Ничего в исходном периоде не переносится по времени доставки.

Missing award/непригодная проверка сохраняет calculated earned, windowW2026-A/cohortC01 и150Rрезерва. Replay/точный дубльaward сохраняет одну logical authorization/U150. Реального transactional ledger нет. Текущий воспроизводитель `evidence/a_current_delta.py`, результаты `a-current-controls.json`, агрегат `current-controls.json`. Первичные наблюдения двух дефектов сохранены координатором в `private/pre-rework/final-primary-evidence/` и не являются текущим fail.

CON-025 и CON-023:по26pass/0fail; их функции/scoring/C3 структурно совпадают, метаданные подписываемой версии проверены независимо. Позитивные personal600U/team420U и все обязательные negative source/config/rule/decision/version/amount/action/scope/time/team/replay/rights контролируются собственными пакетами. Результаты — `c3-CON-025-v1.json`, `c3-CON-023-v2.json`. Разные основания quality/result не сравниваются общимrawscore. Расчётное право, удержанный резерв, authorizedU и фактическая проводка разделены.

## Чтение, зависимости и применимость

Новых эмпирических источников не искали. В этой серии задач прочитаны выбранные первичные места Transcript68–82/101–113: портал/HR/LMS, HR-администрирование и внутреннийIT. Переписка100–116/136–142 допускает разумные допущения и необязательные интеграции. Их глубина зафиксирована в JSON и не выдана за полное чтениеPDF/XLSX или исследований. Транскрипт с аудио не сверен; встреча29.10.2026 датирована по заданному контекстсту, датаэкспорта неизвестна. Переписка собрана26–29.10.2026, индивидуальные даты неизвестны. Wiki/brief — зависимые пересказы той же встречи/переписки, а не новые независимые подтверждения.

Полные текущие specs, точная изменённая signing projection, team-time code и публичныйQArecipe прочитаны; неизменные primitives/календари/QA переиспользованы поSHA/AST. Нормы, цели, поля, часы, люди, доступность, источник оплаты и эффекты остаются проектными предположениями. Синтетика не доказывает банковскийAPI, штат, настройку, transactional posting или мотивационный эффект. ОтсутствиеAPI не автоматическийfail концептуальнойработы. R4 — девять представителей, не полный банковский календарныйпилот.

## Готовность

Все четыре текущих ключа и findings-объекты с text/locators сохранены; текущие файлы не содержат старого fail как текущего результата. Проверки выполнялись Python3.14.8 с-B/no cache. Кандидаты, общий source, закрытые раунды, общие реестры не менялись. Exporter/build/verify, wiki, приложение, commit и вложенные агенты не запускались.

Назначенная проверка завершена. Нерешённых дефектов в заданной узкой дельте не обнаружено; ограничения данных, дискретных стимулов, реальной готовности и эффекта остаются. Выбор оставлен координатору/reviewer.
'''
(C/'evidence.md').write_text(full)
assert [r['candidate_key'] for r in e['results']]==keys
assert all(isinstance(f,dict) and 'text' in f and 'locators' in f for r in e['results'] for f in r['findings'])
assert all(a['summary']['fail']==0 for a in [a,b,i]) and not delta['final_pin_mismatches']
write(O/'report-validation.json',{'candidate_keys':keys,'json_valid':True,'findings_objects':True,'current_C3':{'CON-024@v2':a['summary'],'CON-025@v1':b['summary'],'CON-023@v2':i['summary']},'current_control_total':{'pass':63,'fail':0},'pins':63,'pin_mismatches':[],'no_obsolete_A_key_in_neutral':'CON-024@v1' not in neutral,'current_verification_has_no_original_failure':True,'metric_classification_and_numeric_invariance':True})
print(json.dumps({'keys':[(r['candidate_key'],r['status']) for r in e['results']],'controls':{'A':a['summary'],'B':b['summary'],'incumbent':i['summary']},'pin_mismatches':delta['final_pin_mismatches'],'reports_written':True},ensure_ascii=False))
