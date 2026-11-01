import sys
sys.dont_write_bytecode=True
import json,csv,hashlib,copy
from pathlib import Path
O=Path(__file__).resolve().parent;R=O.parents[1];C=R/'checks';R2=R.parent/'002'
def read(p):return json.loads(p.read_text())
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def finding(id,text,locators,status='supported',kind='own_calculation'):
 return {'id':id,'text':text,'locators':locators,'verification_status':status,'epistemic_type':kind}
freeze=read(R/'private/versions-before-checks.json')['files'];pinbad=[k for k,v in freeze.items() if sha((R/'private/pre-rework'/k) if k.startswith('branches/A') else (R/k))!=v]
inputchecks={p.name:sha(p)==sha(R2/'inputs'/p.name) for p in (R/'inputs').iterdir() if p.is_file() and p.name!='manifest.json'}
sourcechecks=[]
for folder in ['fixtures','round002-stress']:
 root=R/'supporting'/folder
 for x in read(root/'manifest.json')['files']:sourcechecks.append({'path':str((root/x['path']).relative_to(R)),'pass':sha(root/x['path'])==x['sha256']})
inc=[]
for p in (R/'supporting/previous-best').rglob('*'):
 reference=R2/'branches/B/con-023'/p.relative_to(R/'supporting/previous-best')
 if p.is_file() and reference.exists():inc.append({'path':str(p.relative_to(R)),'pass':sha(p)==sha(reference)})
write(O/'integrity.json',{'frozen_files':len(freeze),'pin_mismatches':pinbad,'frozen_inputs_equal':inputchecks,'source_files':len(sourcechecks),'source_checks':sourcechecks,'incumbent_copied_files':inc,'qa_recipe_sha256':sha(R/'supporting/qa-neighborhood-recipe.json')})
# Fixed-window outputs depend on unchanged normal and are reused without alteration.
windows=[]
for row in csv.DictReader((O/'primitive-windows-base.csv').open()):
 keys=['CON-024@v1'] if row['candidate_key']=='CON-022@v1' else ['CON-025@v1','CON-023@v2'] if row['candidate_key']=='CON-023@v2' else ['BASELINE'] if row['candidate_key']=='BASELINE' else []
 for key in keys:x=dict(row,candidate_key=key);windows.append(x)
with (O/'personal-windows.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=list(windows[0]));w.writeheader();w.writerows(windows)
a=read(O/'a-c3-specific.json');b=read(O/'c3-CON-025-v1.json');i=read(O/'c3-CON-023-v2.json')
acontrols=[{'control':'positive_bound_team_member','expected_U_R':150,'observed':a['positive'],'status':'pass' if a['positive']['top_U_R']==150 else 'fail'}]
for k in ['team_source_before_effort','external_config_changed_same_signature']:acontrols.append({'control':k,'expected_U_R':0,'observed':a[k]['observed'],'status':'pass' if a[k]['observed']['top_U_R']==0 else 'fail'})
write(O/'current-controls.json',{'path_base':'analysis/iterations/iteration-007/rounds/003','results':[{'candidate_key':'CON-024@v1','controls':acontrols,'summary':{'pass':sum(x['status']=='pass' for x in acontrols),'fail':sum(x['status']=='fail' for x in acontrols)}},b,i,{'candidate_key':'BASELINE','scope':'No performed local award instructions/amounts in working source','status':'not_computable'}],'limits':['Hypothetical in-memory actions only; public source not altered.','Authorized U is distinct from calculated right and from real ledger posting.']})
refs=[{'path':'checks/evidence/independent-units.csv','locator':'candidate_key exact; scenario/period/subject'},{'path':'checks/evidence/independent-persons.csv','locator':'candidate_key exact; scenario/period/subject'},{'path':'checks/evidence/qa-neighborhood.csv','locator':'control/candidate_key/subject'},{'path':'checks/evidence/current-controls.json','locator':'candidate_key exact; control'},{'path':'checks/evidence/personal-windows.csv','locator':'candidate_key exact; scenario/window/subject'}]
common=[finding('C1','Frozen inputs, source manifests, recipe and candidate pins checked; no source/candidate writes. Reused primitive tables pinned by SHA and structural invariance.',['checks/evidence/integrity.json','checks/evidence/metric-invariance.json'],'supported','file_integrity'),finding('C5','Личные fixed windows и normal остаются прежними. R4 — девять представителей, не полный банковский census. QA-факт, доставка, реальная просрочка, hire/transfer и исходное окно различаются; права не погашаются из-за отсутствующей подписи.',['checks/evidence/personal-windows.csv','../002/checks/evidence/calendar.csv','supporting/round002-stress/dictionary.md'],'supported','reused_independent_calculation'),finding('C6','Портал, HR/LMS и HR-администрирование подтверждены выбранными первичными местами; Jira/CRM/поля/QA/цели/штат/эффект остаются проектными предположениями. Отсутствие реальных API не является автоматическим fail.',['knowledge/raw/Transcript.md:72–80,102–105,112','knowledge/raw/additions_2026-10-29/organizer/discussion_2026-10-26_29.txt:112–116,136–142'],'supported','source_statement_reused')]
A=[finding('A-Q','Фиксированные категории не зависят от соседей: QA100 при полном QA означает ни одного наблюдаемого penalty; 99≤QA<100 — strong с замечаниями. QA98 может пройти normal, но не stretch. Mean99/99.05 не объединяют концы через мостик.',['branches/A/con-024/metrics-spec.json#/quality/recognition_categories','branches/A/con-024/concept.md:sections2,8','checks/evidence/qa-neighborhood.csv']),finding('A-Q-BOUNDARY','Q99_down3958/40=98.95:normal/неstretch. Q99_up3962/40=99.05:normal/stretch, category1/rank21/top0, как99. Q100_down4398/44:normal/stretch, category1/rank20/top0 вместо300. Остальные19zero делят6000:floor315 лично,15R не выдано.',['supporting/qa-neighborhood-recipe.json','checks/evidence/qa-neighborhood.csv','checks/evidence/qa-ties.json']),finding('A-Q-LIMIT','Ноль наблюдаемых штрафов — содержательная дискретная граница полного проверенного портфеля; это не доказанное будущее превосходство по0.0455балла. Скачок300→0, разные размеры портфелей, риск сокрытия/оспаривания minor и широкие ничьи остаются. Непрерывность fixed-slot выплат не требуется.',['branches/A/con-024/concept.md:sections2,8','checks/evidence/qa-ties.json'],'supported','design_interpretation_with_limit'),finding('A-C3-CONFIG','Внешняя matching business-config после подписи изменена baseline_value:null→0; старое разрешение остаётся authorized150U/errors[]. Exact config binding обязателен; независимо ожидаетсяU0 при сохранённом calculated earned и window.',['branches/A/con-024/evaluator.py:49–59,404–408','checks/evidence/a-c3-specific.json:external_config_changed_same_signature','checks/evidence/a_c3_probe.py'],'contradicted'),finding('A-C3-TIME','TeamT07 source-review до усилия (01.11.2025) с хорошим personal-review и заново связанным current source всё равно разрешает150U/errors[]. Независимо ожидаетсяU0: выполненный team-review должен быть послеclose.',['branches/A/con-024/evaluator.py:389–394','checks/evidence/a-c3-specific.json:team_source_before_effort','checks/evidence/a_c3_probe.py'],'contradicted')]
B=[finding('B-SCORE','Все аналитические функции, включая QA/scoring/C3, структурно совпадают с неизменной результатной политикой. Изменены только candidate/version/parents metadata в metrics-spec; новая бронь не меняет право, scoring или U. Ресурсную дельту проверяет финансист.',['checks/evidence/metric-invariance.json','branches/B/con-025/metrics-spec.json','checks/evidence/c3-verification-CON-025-v1.json'],'supported','structural_invariance'),finding('B-C3','26 текущих C3 controls проходят: personal600U/team420U на independently byte-equal пакетах, точные source/registry/member/config/rule/decision/version/amount, action/scope/time/team negatives удерживаютU0; права/окно/conditionalceiling и один replay-key сохранены. Реального ledger нет.',['checks/evidence/c3-CON-025-v1.json','checks/evidence/b_c3_current.py'])]
I=[finding('I-UNCHANGED','Политика, source и артефакты неизменны. Собственные прежние primitive→metric результаты повторно использованы поSHA; новое качество или новая бронь этому варианту не приписаны.',['checks/evidence/integrity.json#/incumbent_copied_files','supporting/previous-best/metrics-spec.json','checks/evidence/independent-units.csv'],'supported','reused_independent_calculation'),finding('I-C3','26 текущих independently expected C3 controls проходят: personal600U/team420U; stale config/source/rule/decision/version/amount и непригодные action/time/team удерживаютU0, replay сохраняет одну логическую авторизацию.',['checks/evidence/c3-CON-023-v2.json','checks/evidence/c3-verification-CON-023-v2.json'])]
BASE=[finding('BASE-NC','На38source и общих QA-пробах нет фактических назначений руководителя/сумм/формулы локального конкурса; local metric→rank→award not_computable, не0реальныхназначений. CorporateC/R и1:1 переиспользованы из frozenexcerpt.',['inputs/baseline.md:7–20,45–55','checks/evidence/qa-neighborhood.csv:BASELINE'],'supported','reused_case_excerpt')]
results=[]
for key,status,findings,c3 in [('CON-024@v1','unsupported',A,'fail_two_controls'),('CON-025@v1','supported',B,'pass_26_current_controls'),('CON-023@v2','supported',I,'pass_26_current_controls'),('BASELINE','partial',BASE,'not_computable_local_source')]:
 results.append({'candidate_key':key,'status':status,'scope':'Listed frozen policy, synthetic calculations and current controls only; no measured bank causal effect/readiness','evidence_refs':refs,'checks':{'C1':'pass' if not pinbad else 'fail','C2':'own_rank_and_recipe_or_pinned_primitive_invariance','C3':c3,'C5':'unchanged_windows_and_source_scope','C6':'source_statements_separate_from_assumptions'},'findings':common+findings,'calculation_paths':['checks/evidence/quality_delta.py','checks/evidence/independent-units.csv','checks/evidence/independent-persons.csv','checks/evidence/qa-neighborhood.csv','checks/evidence/qa-ties.json','checks/evidence/current-controls.json','checks/evidence/personal-windows.csv'],'unresolved':['Bank field/API availability, independent staff and actual source/QA readiness are assumptions.','Real transactional posting and motivational effect are not tested.']+(['Two concrete C3 failures require targeted rework and independent delta.'] if key=='CON-024@v1' else [])})
previous=read(R2/'checks/evidence.json')
write(C/'evidence.json',{'schema_version':1,'stage':'initial_round003_independent_checks','path_base':'analysis/iterations/iteration-007/rounds/003','results':results,'method':'Reuse own primitive data on hash and AST invariance; independently recompute all categorical rank/money and five QA snapshot controls. Observe pure AST functions only for current C3, with independently reconstructed exact packages/amounts. No author self-test or evaluator as metric oracle.','reading_log':previous['reading_log']+[{'path':'supporting/qa-neighborhood-recipe.json;branches/A/con-024;branches/B/con-025','version_date':'01.11.2026, frozen round003','actual_reading_depth':'full recipe and metrics specs; exact changed scorer/rank/C3 code; concept sections2/8 and source-to-award; unchanged primitives reused by hash/AST','design':'prospective synthetic policy and engineering controls','dependency_group':'same synthetic source; candidate documents not empirical validation','limitations':'No bank data/API or motivational outcome observed.'}],'publication_dependencies':'Same meeting and organizer written-thread remain underlying primary sources; derived summaries do not count as independent evidence. No new external study/search.','verification':{'candidate_keys':[r['candidate_key'] for r in results],'frozen_pins':len(freeze),'source_files':len(sourcechecks),'38_snapshots_reused':True,'new_categorical_rank_rows':2600,'new_rank_differences':len(read(O/'metric-invariance.json')['A_new_rank_differences']),'QA_recipe_snapshots':5,'full_metric_sweep_repeated':False,'current_C3':{'CON-024@v1':{'pass':1,'fail':2},'CON-025@v1':b['summary'],'CON-023@v2':i['summary']}}})
full='''# Независимые доказательства: раунд003

Первичная проверка текущих CON-024@v1, CON-025@v1, CON-023@v2 и BASELINE. Выбора победителя нет. Источники синтетические; финансовую и ресурсную дельту проверяет отдельный финансист.

## Метод и C1

Собственные primitive→unit/QA/normal/R4 результаты раунда002 повторно использованы с SHA в `evidence/metric-invariance.json`. На новом коде доказана структурная неизменность A primitive/normal/QA кроме явно заменённого rank, а также всех аналитических функций B. Большой sweep неизменных функций не повторялся. Новые категориальные rank/money самостоятельно пересчитаны для всех2600unit-строк; расхождений с сохранёнными авторскими CSV нет. Авторский evaluator не был метрическим oracle. Для C3 его чистые AST-функции использованы только как наблюдаемый проверяемый алгоритм; ожидаемые суммы и canonical package построены независимо.

`evidence/integrity.json`: финальные pins, пять inputs,41source-файл, точная копия CON-023 и рецепт проверены без изменений исходников. Recipe SHA256=b5ce8d3d8b0442879526be9916e657371b1929f5d1f469cab1751ed334192a12. Все записи только в назначенных checks. Python3.14.8, -B/no cache; закрытые exporters/verify/build не выполнялись.

## Новый scorer и QA-пробы

Fixed category2 означает ни одного наблюдаемого penalty в полном совместимом QA: mean100 при max score100. Category1 означает прежний stretch99≤mean<100 с подтверждённым замечанием. Категории не зависят от соседей; мостик99.05 не сливает99 и100. QA98 может пройтиnormal, но неstretch. Все прежние требования полного охвата, зрелости, минимального наблюдения и независимости сохранены.

| Проба | Точный QA | Normal/stretch | Категория, ранг, личный top |
|---|---|---|---|
| Q0/S11 | 3960/40=99 | Да/да | 1,rank21,0R |
| Q99_down/S11 | 3958/40=98.95 | Да/нет | Нижеstretch,0R |
| Q99_up/S11 | 3962/40=99.05 | Да/да | 1,rank21,0R |
| R2.precision/S11 | 3962/40=99.05 | Да/да | 1,rank21,0R |
| Q100_down/S21 | 4398/44=2199/22 | Да/да | 1,rank20,0R вместо300R |

После Q100_down остаются19участников без замечаний:6000/19R до личногоfloor,315R каждому и15R не выдано. Источник и40/44 знаменатели не подбирались: изменён только заданный minor/score и physical SHA копии. В `evidence/qa-neighborhood.csv` все четыре варианта; `qa-ties.json` хранит составы и размах ничьих. У результатных CON-025/023 эти QA-пробы не меняют объёмный ранг; BASELINE честно not_computable.

Граница100 имеет опубликованный наблюдаемый смысл: один подтверждённый minor опровергает категорию «без замечаний». Она не доказывает лучшего будущего качества по разнице0.0455балла. Поэтому это не chaining под новым названием, но скачок300→0, разный размер полного портфеля, стимул скрывать/оспаривать minor и широкие ничьи остаются существенными ограничениями. Непрерывность fixed-slot выплат не требуется, а полезность политики не измерена.

## C3 и обязательные дефекты

CON-024@v1 имеет два подтверждённых дефекта. Позитивная independently bound подпись P031 даёт150U. Однако выполненный teamT07 source-review от01.11.2025 до усилия, при хорошем personal-review и заново связанном current source, тоже даёт150U/errors[]. Вторая проба меняет matching external business-config baseline_value:null→0 после подписи: старое разрешение остаётся150U/errors[]. Независимо требуетсяU0 с сохранённым calculated earned/window. Внешний PUBLIC_CONFIGS не включён в signed source/rule projection; время team source-review не сопоставляется сclose. Locators: `evidence/a-c3-specific.json`, `a_c3_probe.py`; evaluator.py:49–59,389–408. Это единый must-fix из двух пунктов; кандидаты нами не исправлялись.

CON-025 и неизменная CON-023 каждый прошли26актуальных C3контролей. Independently byte-equal пакеты разрешаютpersonal600U/team420U; source/registry/member/config/rule/decision/version/amount и performed action/time/scope/team negatives удерживаютU0. Отсутствие подписи/источниковой проверки сохраняет calculated right/rank/window, реальная потеряsource сохраняет pending и conditional group ceiling6000. Два квартала имеют один fixed-window Gkey и ceiling2500, а не два начисления. Повторный расчёт/доставка award-акта сохраняет одну logical authorization/U600. Реального transactional ledger нет. См.`evidence/c3-CON-025-v1.json`, `c3-CON-023-v2.json`, `b_c3_current.py`.

## Источники и предел чтения

Новых эмпирических источников не искали. В этой серии задач ранее прочитаны выбранные первичные места Transcript68–82/101–113: портал/HR/LMS, HR-администрирование, внутреннийIT; письменная переписка100–116/136–142 допускает разумные допущения и необязательные интеграции. Их прежняя глубина сохранена в reading_log, не выдана за полное чтениеPDF/XLSX/исследований. Транскрипт не сверен с аудио; meeting29.10.2026 по заданному контексту, датаэкспорта неизвестна. Переписка собрана26–29.10.2026, индивидуальные даты ответов неизвестны. Wiki/brief зависят от той же встречи и не добавляют независимых доказательств.

Нормы, цели, часы, поля, readiness и люди — проектные предположения. Внешних причинных коэффициентов нет. Пройденная синтетическая функция не доказывает реальные API, доступный штат, настройку или эффект мотивации. Отсутствие API не автоматическийfail концептуальной работы, но не снимает внутренние C3противоречия. R4 — девять представителей, а не полный банк; окна, фактический поздний результат и поздняя доставка своевременного QA сохранены отдельно.

## Состояние

Первичный JSON содержит четыре ключа и findings-объекты с text/locators. Незавершено: целевой rework CON-024 по двум C3 дефектам и узкая независимая дельта. Никаких новых гипотез, app/wiki/commit или вложенных агентов не создавалось. Победитель не выбирался.
'''
(C/'evidence.md').write_text(full)
neutral='''# Текущая проверка доказательств

01.11.2026. CON-024@v1, CON-025@v1, CON-023@v2 и BASELINE проверены на одном synthetic source:38снимков и пяти общих QA-копиях. Выбор не делается. Финансы и помесячную мощность рассматривает отдельный отчёт.

| Вариант | Проверенный результат | Ограничение |
|---|---|---|
| CON-024@v1 | Категории наблюдаемого качества:QA100 без penalty выше strong99≤QA<100; новый rank независимо восстановлен для2600unit-строк | ДваC3контроля не проходят; одинminor может изменить top300→0R |
| CON-025@v1 | Результатный scoring сохранён;26C3контролей проходят | Новая помесячная бронь оценивается отдельной финансовой проверкой |
| CON-023@v2 | Результатный scoring и26C3контролей подтверждены | Реальные люди/API/ledger и эффект не установлены |
| BASELINE | Руководитель назначаетR в пределахфонда | Нет фактических назначений вsource:localrank/awardnot_computable |

CON-024:99и99.05 имеют одну категорию/rank21/top0, а100 остаётся отдельной категорией. 98.95=3958/40 проходитnormal, но неstretch;99.05=3962/40 проходит оба. В Q100_down одинminor даёт4398/44=99.954545…:normal/stretch сохраняются, категория «без замечаний» утрачена,rank20/top0 вместо300. Оставшиеся19участников без penalty делят6000R:floor315лично,15Rневыдано. Данные/IDs/40и44инспекции не подбирались, общийрецепт соблюдён.

Chaining нет: класс не зависит от соседей и мостик не объединяет99/100. Граница100 означает отсутствие наблюдаемого penalty в полном совместимомQA, а не лучшее будущее качество по0.0455балла. Скачокденег, разныеполныепортфели, риск сокрытия/оспариваний и широкие ничьи остаются. Fixedслоты не обязаны давать непрерывную выплату. Полезность такой границы сотрудникам пока не проверена.

CON-024 C3: позитивная выполненная bound подпись даёт150U, но team-review доусилия и изменение внешней matchingbusiness-config после подписи тоже дают150U/errors[]. Независимо требуетсяU0 и сохранение отдельного calculatedearned/window. Locators:`checks/evidence/a-c3-specific.json`. ДляCON-025/023 каждый набор26positive/negativeконтролей проходит:personal600U/team420U, stale source/config/rule/decision/version/amount и непригодные action/scope/time/team удерживаютU0. Повторная доставка сохраняет однуlogicalauthorization;U — состояние, не реальнаяпроводка. Текущие результаты:`checks/evidence/current-controls.json`.

Normal абсолютен и полныйQA обязателен. Source-review не award-разрешение. Нет подписи — сохранённое право/условныймаксимум, не нулеваяработа. G2500 связывает первые два квартала одногоfixedwindow раз в12месяцев;R4девятипредставителей не полныйcensus. Worklog не мощность, FTE/сложность не применяются дважды; одинroot/benefit не размножается.

Портал/HR/LMS/HR-администрирование подтверждены выбранными первичными местами Transcript39:18–43:03/50:26,строки72–80/112. ПродуктыCRM/Jira,поля,QA,цели,штат,готовность и причинныйэффект остаются допущениями. Пересказы однойвстречи не независимые подтверждения;PDF/XLSX и внешние исследования здесь не перечитывались. РеальныеAPI не требуются для концептуальной проверки; синтетика не доказывает внедрение/мотивационныйэффект.
'''
(C/'evidence-for-review.md').write_text(neutral)
assert not pinbad and all(inputchecks.values()) and all(x['pass'] for x in sourcechecks) and all(x['pass'] for x in inc)
assert len(results)==4 and all(isinstance(f,dict) and 'text' in f and 'locators' in f for r in results for f in r['findings'])
write(O/'report-validation.json',{'candidate_keys':[r['candidate_key'] for r in results],'pins':len(freeze),'pin_mismatches':pinbad,'source_files':len(sourcechecks),'A_independent_rank_differences':len(read(O/'metric-invariance.json')['A_new_rank_differences']),'current_C3':{'CON-024@v1':'1pass/2fail','CON-025@v1':b['summary'],'CON-023@v2':i['summary']},'json_valid':True,'findings_objects':True})
print(json.dumps({'written':True,'pins':len(freeze),'source_files':len(sourcechecks),'keys':[(r['candidate_key'],r['status']) for r in results]},ensure_ascii=False))
