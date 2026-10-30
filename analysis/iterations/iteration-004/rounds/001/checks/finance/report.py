#!/usr/bin/env python3
"""Render the contracted check from independently recomputed CSVs. No ranking."""
import csv
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
CHECKS=HERE.parent
A=list(csv.DictReader((HERE/'annual.csv').open()))
EX=list(csv.DictReader((HERE/'monthly-execution.csv').open()))
LONG=list(csv.DictReader((HERE/'ten-year-conditional.csv').open()))
KEYS=['BASELINE','CON-006@v2','CON-009@v1','CON-010@v1']
PATHS=['checks/finance/'+s for s in ['model.py','report.py','annual.csv','monthly-required.csv',
       'monthly-execution.csv','ten-year-conditional.csv','direct-R-services.csv',
       'comparable-costs.csv','rights-lifecycle-tests.json','new-promise-limits.json',
       'audit-assumptions.json','source-manifest.json','verification.json']]
def n(row,k):return float(row[k])
def t(row,k):return row[k]=='True'
def get(key,sid):return next(x for x in A if x['candidate_key']==key and x['scenario']==sid)
def million(x):return f'{x/1e6:.6f}'.rstrip('0').rstrip('.')
def state(ok):return 'pass' if ok else 'fail'

COMMON_REFS=[
 {'path':'inputs/baseline.md','locator':'Единая сценарная экономика M04; Каталог, касса и получение; Остатки, резерв и следующие периоды; Полные общие параметры M04'},
 {'path':'inputs/evidence.md','locator':'C01/C02/C05/C06/C07/C08; точные первичные locators сохранены во frozen-пакете'},
 {'path':'knowledge/raw/задание_кейса_с_диска/Кейс_ОТП_1 тур_CL Cup Moscow 2026.pdf','path_base':'OTP_bank','locator':'физ.с.10–12: валюты/fixed;14–15: квартальный F и Q3;19:30–34млн закупок'},
 {'path':'knowledge/raw/Transcript.md','path_base':'OTP_bank','locator':'13:12–14:01,стр.20–21;18:52–19:26,стр.30–31: сохранение прав;55:33,стр.133: против KPI расхода;57:09,стр.138: партии'}]
findings={
 'BASELINE':[
  'Сценарное повторение Q3:154.160m R фонд/год,77.710364m личных R/год,76.449636m невыданного F закрывается. Не факт годового расхода ОТП.',
  'CORE требует39.673m RUB кассы и3401.8394 корзины/месяц при общей мощности3000; LOW full-new41.516m. Fail обоих закупочных лимитов относится только к Q3-экстраполяции на M04, а не доказывает фактический перерасход действующей программы.',
  'Низкое использование новых R не решает проблему: при0% касса24.638m, но полный резерв этих новых R15.075811m; вместе39.713811m. При60%33.659m кассы+6.030324m резерва также превышает34m.',
  'При ограниченном исполнении нельзя показывать условный остаток217.6m как фактический. В явном плане исполнения при30m CORE: касса29.973m, неисполненные9922.0728 корзины, личные C/R267.210364m.',
  'Балансовый gate pass означает сохранение известных модельных прав и равенств; фактические непроведённые начисления и заказы неизвестны. Неизвестные управленческие/IT-часы baseline не приравнены нулевой цене.'
 ],
 'CON-006@v2':[
  'Механика сохранена буквально: будущие fixed_C=0 и новые R/F=0;7200 натуральных J год1,600 вручений/месяц. Это иной объём будущего вознаграждения, а не сопоставимое сохранение fixed.',
  'На одинаковых старых200m C/R, доле20%, корзине970RUB и партиях100: CORE требует14.841m кассы, HRпик165.7778h, полностью7200J исполнены. Старые M01/M02 цифры автора не перенесены на M04.',
  'J не валюта без обязательств: при личной отсрочке всех сохраняются7200J и6.984m RUB покрытия через10лет; следующего J до добровольного получения+12месяцев нет. Задержка банком создаёт отдельное нарушение и может накопить14400J, а не удалить первое право.',
  'Полный старый+новый J стресс45.881m кассы и превышение физических/HRмощностей; январский пик14.841m годовой кассы помещается, но месячные выдача/HR254.6667h не помещаются. Низкая годовая цена не обеспечивает все старые права.',
  'Budget pass ограничен CORE20% старых+100%J; на требования сохранения fixed и кейсовой пригодности этот финансовый pass не распространяется. Источники/доступность/полномочия банка остаются uncertain.'
 ],
 'CON-009@v1':[
  'Весь новый фонд8m R/год,2m/q;40 владельцев и их календарь650/650/700тыс. сверены отдельно, включая региональные60/40. Невыданный F не личное право, одобрение до проводки уже покрывается.',
  'LOW_FIXED96_FULL_NEW:100% новых96m C и8m R плюс40m старого спроса; касса28.033m, HR187.1778h peak, месячная выдача2406.6667 корзины. Условный pass при30 и34, без изменения fixed-ставок/оснований.',
  'CORE26.190m и HR182.9111h проходят, но57.6m новых fixed C остаются с будущей стоимостью11.1744m RUB. CORE не полное покрытие новых fixed.',
  'FIXED80/OLD35/PRICE20/LOW96_OLD35/LOW96_PRICE20: касса требует34m. В них A проходит региональную и HRмощность; fixed100,all-rights,регион80,январь и концентрация всех новых R в декабре не проходят соответствующие лимиты.',
  'Полная сопоставимая известная стоимость38.2718m CORE/40.358m LOW включает6мин на все получения, подготовку и все роли; процессные затраты не доказали окупаемость. Дополнительный труд самой уже выполненной полезной работы не известен и не объявлен нулевой ценой.',
  'При двойном труде HR365.8222/374.3556h peak выше220;25% замещение требует дополнительной кассы сверх закупок. Личные неисполненные C/R и полный резерв новых R сохраняются.',
  'Существенной арифметической ошибки, требующей изменения версии для основного LOW gate, не найдено. Достаточно единых checks; реальный rollout uncertain.'
 ],
 'CON-010@v1':[
  'Максимум4*(300*5000+10*(30000+15000+5000))=8m R; один пул на командный результат, не на каждого участника. 5-членная команда I:55тыс. суммарно с базой; ничья не добавляет мест. Разбиение пула для k2..5 сохраняет сумму.',
  'Условное обещание и покрытие2m R возникают до усилия, а личное начисление/получение в месяцах3/6/9/12. Неисполненные проверки и одобренные непроведённые права не становятся невыданным свободным F.',
  'LOW full-new: касса28.033m и HR213.4444h peak при220 проходят; CORE26.190m и209.1778h проходят кассу/мощность, но не все новые fixed. Учтены600 персональных апелляций/q и отдельная оценка пилота в месяце4.',
  'FIXED80 при34m проходит кассу31.719m, но HR221.9778h; OLD35 касса32.010m, но физический пик3006.6667 корзины и HR222.5111h fail. LOW96_OLD35 касса33.853m, но3166.6667корзины/HR226.7778h fail. Нельзя называть кассовый pass обеспеченным исполнением.',
  'Авторские37.1608m CORE/39.055m LOW воспроизведены, однако их граница не включает6мин на все получения, включённые A. Общая AUD01:39.8488m/41.935m с полезной работой2.4m; без самой полезной работы37.4488m/39.535m. Поэтому процедура B дешевле A в этой модели, а полный ресурс с дополнительной работой выше; это не однозначный финансовый победитель.',
  'Общий ресурсный аудит25% замещения и двойного труда включает и6мин получения. HR при2x418.3556/426.8889h fail220. Расходы обслуживания существующей платформы неизвестны сверх известных сумм.',
  'Квартальные сроки после25-го до конца месяца требуют подтверждённых запаса/номиналов/логистики; месячный агрегат этого не доказывает. Все новые R в декабре дают физический/HRfail даже при годовом кассовом pass.',
  'Нужна корректировка сопоставления полной стоимости в checks, а не изменение финансовой механики/версии. Основной LOW gate pass в явных допущениях; реальные банковские входы/даты uncertain.'
 ]}
results=[]
for key in KEYS:
 refs=COMMON_REFS.copy()
 if key=='CON-006@v2':
  refs += [{'path':'../../incumbent/policy-spec.json','locator':'currency;new_rights;workload;rewards'},
           {'path':'../../incumbent/concept.md','locator':'разделы2/4; неизменённая механика J и I_C/W_R/G_R=0'}]
 elif key!='BASELINE':
  branch='A' if key=='CON-009@v1' else 'B'
  refs += [{'path':f'branches/{branch}/finance-spec.json','locator':'new_R_policy/workload/resource_calendar' if branch=='A' else 'promise_formula/calendar/resource_parameters/pilot'},
           {'path':f'branches/{branch}/concept.md','locator':'разделы2/4/6; это проектные решения/допущения'}]
 scope=(
  'Fail бюджета в CORE_60 и LOW_FIXED96_FULL_NEW при сценарном повторении Q3 на общей M04. Балансовый pass только для сохранения идентифицированных прав и модели исполнения; реальный годовой baseline не доказан.' if key=='BASELINE' else
  'Pass только M04 CORE:20% старых200m C/R+100%7200J, нулевые будущие fixed/R как в неизменённой концепции. Сохранение fixed не заявляется; all-rights/январь вне pass; банковский rollout uncertain.' if key=='CON-006@v2' else
  'Pass в M04 LOW_FIXED96_FULL_NEW: fixed96m по прежним правилам,100%новых fixed/R8m,20%старых200m,цены940+30RUB/корзина,география60/40,партии100,заказm0,HR220. CORE только частичное предъявление fixed60%, а не полное покрытие. Непроходящие стрессы ниже; реальный rollout uncertain.')
 if key=='CON-009@v1':scope+=' Ресурсный pass при7200 карточках/год,5% апелляций и10% выборке/устных/межкомандных случаев; это сценарные частоты, не максимум всех возможных обращений.'
 if key=='CON-010@v1':scope+=' Ресурсный pass включает28800 намерений/год,720 результатных карточек и2400 персональных апелляций/год, но фактическая длительность операций неизвестна.'
 scenarios=[]
 for a in [x for x in A if x['candidate_key']==key]:
  scenarios.append({'scenario':a['scenario'],
   'budget_cash_30':state(t(a,'required_cash_pass_30')),'budget_cash_34':state(t(a,'required_cash_pass_34')),
   'budget_cash_plus_R_reserve_30':state(t(a,'cash_R_reserve_pass_30')),
   'budget_cash_plus_R_reserve_34':state(t(a,'cash_R_reserve_pass_34')),
   'physical_capacity':state(t(a,'required_capacity_pass')),'HR_capacity':state(t(a,'HR_capacity_pass')),
   'required_cash_RUB':n(a,'required_cash_RUB'),'HR_peak_hours':n(a,'HR_peak_hours'),
   'new_R_reserve_RUB':n(a,'new_R_reserve_RUB'),
   'unredeemed_current_fixed_exposure_RUB':n(a,'unredeemed_current_fixed_exposure_RUB'),
   'all_current_new_promises_requested':(key=='CON-006@v2' or 'LOW' in a['scenario'] or a['scenario'] in ['FIXED_100','ALL_RIGHTS_100']),
   'interpretation':'Full required demand/cost. If any gate fails, conditional debits/closing balances in annual.csv are not actual. See separately constrained monthly-execution.csv; all unserved claims retained.'})
 results.append({'candidate_key':key,'scenario_scope':scope,
  'gates':{'budget':'fail' if key=='BASELINE' else 'pass','currency_balances':'pass'},
  'real_bank_rollout':'uncertain',
  'evidence_refs':refs,
  'assumption_refs':['inputs/baseline.md#Полные общие параметры M04 (all non-source anchors are assumptions)',
   'supporting/finance-basis/scenario-inputs.json#common/scenarios/actual_bank_inputs',
   'checks/finance/audit-assumptions.json#AUD01–AUD05']+
   ([] if key=='BASELINE' else ['../../incumbent/assumptions.csv' if key=='CON-006@v2' else 'branches/'+('A' if key=='CON-009@v1' else 'B')+'/assumptions.csv']),
  'findings':findings[key],
  'requires_candidate_revision_for_primary_financial_scope':False,
  'revision_limit':'Coordinator decides scope/evidence gates. This check neither changes concepts nor selects a winner.',
  'scenario_results':scenarios,'calculation_paths':PATHS})
out={'schema_version':1,'check_kind':'independent_finance','version':'M04-independent-2026-10-31',
 'classification':'All monetary results are calculations on explicit scenario assumptions; only original rules/budget/Q3 anchors are case facts.',
 'results':results,
 'shared_findings':[
   'No winner selected. Conditional financial pass does not establish effect, acceptability of89.7%prospective fund reduction, or bank deployment readiness.',
   'Old200m C/R exposure38.8m RUB against scenario initial cash reserve0. No accumulated right extinguished by aging, conversion, transfer, queue, quarter-end or nonresponse.',
   'Full current new144m fixed+8m R potential physical cost29.488m before transition; 0.5m buffer leaves only12k at30m. This flow limit omits old demand and batch timing.',
   '100% old+new demand in A/B costs68.385m cash at fixed144 or59.073m at fixed96; consumption68.288/58.976m. Those are required costs, not achieved redemptions.',
   'Same old/new use assumptions across all four; incumbent future currency0 is policy difference, not changed input scenario.',
   'HR20% cash outside narrow procurement gate;25%nonHR replacement and2x labor separately tested. Useful production work shown separately from administrative procedure.',
   'One-month supplier lead, batches100 per region, zero opening stock/AP/cash backing. Inventory consumes procurement cash once; cost of consumption and ending stock are reconciliation, not second charges.',
   'Old40m R direct-services alternative:2000units,16000h,16mresource/4mcash, uniform166.7units/month within200; concentrated demand fails. The same R cannot also redeem physical rewards.',
   'Unknown bank N/grossfixed/oldbalances/unpostedrights/orders/backing/catalog/regional-capacity/labor remain uncertain. They do not invalidate conditional scenario arithmetic, but cannot be filled with invented zeros.'
 ],'verification_path':'checks/finance/verification.json'}
(CHECKS/'finance.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')

lines=[
'# Независимая финансовая проверка M04, iteration-004 / round001',
'',
'31.10.2026. Все четыре варианта пересчитаны собственным [model.py](finance/model.py). Авторские модели, self-check и готовые CSV не импортировались/не исполнялись. Источники/хеши: [source-manifest.json](finance/source-manifest.json). Результат — условная сценарная проверка, не подтверждение реального бюджета или rollout ОТП. Победитель не выбирается.',
'',
'**Границы gates.** A/B имеют финансовый pass только в LOW_FIXED96_FULL_NEW:100% новых96млн fixed C по прежним основаниям/ставкам,8млн R,20% старых200млн C/R,общая корзина/мощности/календарь. 96млн — сценарная частота событий, не урезание правил. CORE означает60% новых fixed и не подтверждает обеспечение всех новых прав. Incumbent pass имеет другую будущую политику fixed/R=0 и7200J; baseline fail относится исключительно к экстраполяции Q3 на M04. Банковская готовность у всех uncertain.',
'',
'| Вариант | CORE / LOW касса, млн руб. | Пик HR CORE / LOW, ч | Gates в названной области |',
'|---|---:|---:|---|']
for key in KEYS:
 c=get(key,'CORE_60');l=get(key,'LOW_FIXED96_FULL_NEW')
 lines.append(f"|{key}|{million(n(c,'required_cash_RUB'))} / {million(n(l,'required_cash_RUB'))}|{n(c,'HR_peak_hours'):.3f} / {n(l,'HR_peak_hours'):.3f}|{'budget fail; balance pass' if key=='BASELINE' else 'budget/balance pass; rollout uncertain'}|")
lines += [
'',
'Факты:30–34млн закупок/год (PDF физ.с.19); R→C1:1, личные C/R сохраняются (с.10–12 и Transcript13:12–14:01,стр.20–21;18:52–19:26,стр.30–31); Q3 F38,54−невыдано19,112409=19,427591млн R (с.14–15). **Допущения:**N7200,старые160млн C/40млн R,fixed144/96млн,спрос,цены/регионы/часы — из frozen M04. **Расчёты:**8млн R — весь будущий фонд, на89,7059% ниже сценарной выдачи77,710364млн/год при фонде154,16млн. Это цена изменения политики, не доказанная эффективность. 24млн — отдельная sensitivity, не базовый ресурс.',
'',
'**Потоки и исполнение.** `Cclose=Copen+fixed+R→C−confirmed physical C`, `Rclose=Ropen+posted R−R→C−confirmed direct R`; внутренние переводы имеют чистый ноль. F, условные обещания, одобренные непроведённые права, личные C/R и J разделены. При блокировке проверки B сохраняет обещание/резерв; при задержке проводки A сохраняет уже одобренное право. Тесты: [rights-lifecycle-tests.json](finance/rights-lifecycle-tests.json). Сценарные нули известных задержек не означают нулевые фактические непроведённые обязательства банка.',
'',
'Нормированная корзина5000C: закупка940руб.+доставка30руб.=970руб.,0,194руб./C. Партия100/регион,лаг1месяц,оплата100%при получении; январские заказыm0 оплаченыm1. Начальные склад/AP/резерв0. В конце месяца оплаченный склад сохраняется, AP0; декабрьский заказ под январь не расход текущего года. Касса и стоимость потребления показаны раздельно: прибавлять склад/потребление к закупке второй раз нельзя. Месячная модель не доказывает наличие конкретных SKU, номиналов и логистику после25-го B.',
'',
'[monthly-required.csv](finance/monthly-required.csv) — полный **требуемый** спрос/касса; при fail его погашения и остатки контрфактуальны. [monthly-execution.csv](finance/monthly-execution.csv) отдельно считает ограниченное исполнение при30/34млн, региональной мощности и HR220ч; неполученное сохраняется в C/R/J и реестре запросов. Явная проверочная политика: годовая касса доступна с начала, известный сценарный прогноз, заказы за месяц, FIFO oldC→oldR→fixed→newR→J; это один возможный порядок, не предписание банку и не оптимизация.',
'',
'Например при30млн и ALL_RIGHTS_100 A/B **требуют68,385млн**, а приведённый ограниченный план тратит29,973млн, оставляет39500 корзин запросов и197,5млн C/R. Разница не экономия. При baseline CORE тот же план сохраняет267,210364млн C/R и9922,073 невыданных корзины; условный остаток217,6млн нельзя выдать за фактический.',
'',
'**Стрессы, кроме основного LOW.** Полная таблица84 сценарных записей — [annual.csv](finance/annual.csv). A и B имеют одинаковую годовую кассу, но разный помесячный риск:',
'',
'| Сценарий | Требуемая касса A/B, млн руб. | A | B |',
'|---|---:|---|---|',
'|CORE, fixed60%, old20%|26,190|касса/мощности pass; все fixed не покрыты|то же|',
'|fixed80%|31,719|pass при34|при34 касса pass, HR221,978 fail|',
'|fixed100%|37,345|касса/выдача fail|касса/выдача/HR fail|',
'|old35%|32,010|pass при34|выдача3006,667/мес. и HR222,511 fail|',
'|цена закупки+20%|31,266|pass при34|pass при34|',
'|LOW96 old35%|33,853|pass при34|выдача3166,667 и HR226,778 fail|',
'|LOW96 цена+20%|33,4662|pass при34|pass при34|',
'|100% всех старых+новых, fixed144 /96|68,385 /59,073|касса/мощности fail|касса/мощности fail|',
'|регион80% /январь50%старого /все новые R в декабре|годовая касса pass|месячная выдача fail|месячная выдача fail|',
'',
'A:650/650/700тыс.R в квартале, группы40владельцев и60/40регионов сходятся. B:300×5000+10×(30000+15000+5000)=2млнR/квартал; командный пул не умножается на k, с базой команда5чел.Iполучает55тыс. Условия/полный резерв до усилия; начисления3/6/9/12.600апелляций/q и оценка пилота вm4 включены. Расширение24млн даёт CORE29,294/LOW31,040млн кассы, но B HR225,178/229,444ч fail; это не автоматическая доступная программа.',
'',
'**Перенос и годы2/10.** Старые200млн C/R имеют экспозицию38,8млнруб. при начальном денежном резерве0. CORE дополнительно оставляет57,6млн новых fixed C стоимостью11,1744млнруб.; свободные3,810млн закупочного бюджета их не обеспечивают. При использовании новых R60/80/0% касса25,511/25,899/24,638млн + полный остаточный резерв0,6208/0,3104/1,552млн. Касса+резерв26,1318/26,2094/26,190млн; конверсия/передача не прекращают покрытие.',
'',
'A/B CORE: C/R217,6→231,68→278,551млн в годы1/2/10, стоимость остатков42,2144/44,94592/54,03891млн. Даже гипотетический перенос свободной30-миллионной кассы оставляет33,78691млн разрыва через10лет без зачёта малого склада. LOW:160→128→21,47484млн, касса28,033→26,287→21,243млн. Свободный бюджет нельзя считать реальным переносимым резервом без политики банка. [ten-year-conditional.csv](finance/ten-year-conditional.csv) также сохраняет новые R при0/60/80% использования и резервирует весь их непогашенный запас, включая предыдущие годы. Пути baseline после первого нарушения обозначены условными, не фактическими.',
'',
'Incumbent на M04: старые права сокращаются при предъявлении20%, новые7200J стоят6,984млнруб. полного исполнения; касса14,841→13,192→8,051млн в годы1/2/10. При добровольной отсрочке7200J сохраняются10лет, будущий цикл сдвигается; задержка банком может удвоить J и нарушает обещание. Полное предъявление старого+J требует45,881млн и не проходит; низкая цена достигнута в том числе прекращением будущих fixed/R.',
'',
'**Одинаковая граница стоимости.** Ниже закупочная касса+известный ресурс всех ролей: HR1000/руководитель1500/сотрудник1000/IT2000руб./ч, включая подготовку. AUD01 одинаково добавляет6мин на каждое оформление/получение, уже включённые A; это открытая общая чувствительность, не факт банка. Существующая поддержка платформы и неизвестный обычный труд baseline дополнительно не обнулены. Таблица — известная нижняя ресурсная оценка, не исчерпывающая смета банка.',
'',
'| Вариант | Буквальная граница CORE / LOW, млн руб. | Единая AUD01 CORE / LOW | AUD01 без самой дополнительной полезной работы |',
'|---|---:|---:|---:|']
for key in KEYS:
 c=get(key,'CORE_60');l=get(key,'LOW_FIXED96_FULL_NEW')
 lines.append(f"|{key}|{million(n(c,'literal_known_cost_on_cash_boundary_RUB'))} / {million(n(l,'literal_known_cost_on_cash_boundary_RUB'))}|{million(n(c,'audit_known_cost_on_cash_boundary_RUB'))} / {million(n(l,'audit_known_cost_on_cash_boundary_RUB'))}|{million(n(c,'audit_process_cost_excluding_useful_RUB'))} / {million(n(l,'audit_process_cost_excluding_useful_RUB'))}|")
lines += [
'',
'В B отдельно2400ч/2,4млнруб. самой полезной работы. Процедура B на общей границе ниже A, а ресурс с этой работой выше. A признаёт уже сделанную работу; обычный производственный труд/польза альтернатив неизвестны и не считаются нулём. Из этих сумм нельзя вывести однозначное преимущество A или ROI. Авторские B37,1608/39,055 подтверждены на его более узкой границе; единое сопоставление исправлено здесь без изменения концепций.',
'',
'HR20% — дополнительная касса вне закупочного gate. AUD01 при25%оплачиваемого замещения остальных ролей требует сверх закупок A2,90481/2,96305млн, B3,30206/3,3603млн (CORE/LOW). При2×всего труда HR A365,822/374,356ч, B418,356/426,889ч, выше220; известный полный ресурс A50,3536/52,683млн, B53,5076/55,837млн. Замещение не доказывает наличие свободных часов. Данные в [comparable-costs.csv](finance/comparable-costs.csv).',
'',
'Прямые R-сервисы — отдельная стоимость: старые40млнR→2000услуг×8ч=16000ч/16млнруб. ресурса и4млнруб.кассы25%замещения,166,7/месяц при мощности200; все в одном месяце не помещаются. Новые8млнR→400услуг/3200ч/3,2млнруб./0,8млнкассы, в одном месяце также fail. Эти R не погашаются ещё раз физически; физический резерв не является одновременно оплатой замещения. Реальные условия отгула ОТП неизвестны. [direct-R-services.csv](finance/direct-R-services.csv).',
'',
'**Проверки и незавершённое.** [verification.json](finance/verification.json):1008месячных требуемых строк,2016строк ограниченного исполнения,200годовых строк переноса; балансы C/R/F/J,склад/AP,бюджет/резерв,партии и годовые максимумы проверены. Запуск из любой папки: `python3 …/checks/finance/model.py`, затем `python3 …/checks/finance/report.py`. Полный контракт:[finance.json](finance.json).',
'',
'Для основного LOW у A/B целевая доработка версии по финансовому gate не требуется: достаточно этого исправленного сопоставления. Реальные grossfixed/остатки/заказы/непроведённые права/обеспечение/региональные SKU/часы/сроки остаются uncertain и подлежат проверке перед запуском. Полный all-rights стресс уже fail; очередь, отказ от выбора, молчание, конец квартала и смена названия права его не устраняют. Финансовая проверка не выбирает концепцию и не доказывает эффект/принятие сокращённого фонда.',
]
(CHECKS/'finance.md').write_text('\n'.join(lines)+'\n')
assert len(out['results'])==4 and {r['candidate_key'] for r in out['results']}==set(KEYS)
for r in out['results']:
 for p in r['calculation_paths']:assert (CHECKS.parent/p).is_file(),p
print('finance.json / finance.md rendered;4 candidates;all calculation paths exist')
