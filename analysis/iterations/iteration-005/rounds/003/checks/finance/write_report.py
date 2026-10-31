#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Package independent results. Writes only assigned checks and finance paths."""
import json,csv
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parent.parent
def js(p):return json.loads(p.read_text())
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
v=js(P/'verification.json');assert v['status']=='pass'
keys=['BASELINE','CON-011@v2','CON-011@v3','CON-015@v1']
scope=('Сценарные годы1–3, стационарный и prospective запуск36месяцев/первые15месяцев, '
       'fixed96млн C/год при прежних ставках, старые личные160млн C+40млн R, old20%/год; '
       'новые fixed/R100% при полном новом обещании, EXPECTED fixed60% отдельно; '
       '5000C корзина940RUB закупка+30RUB доставка, регионы60/40, мощности1800/1200корзин/месяц, '
       'партия100/регион, предзаказ1месяц и оплатаприполучении; исходный склад/резерв0. '
       'Годовой критерий касса+знаковаяΔрезерва+0.5млн буфер≤34млнRUB; '
       'труд/IT вне закупочного лимита. Датированный pass только при пригодном оплаченном '
       'складе, однократно выделенном до14-го, или проверенной отдельной ликвидной замене. '
       'Это условная расчётная область, фактические банковские параметры/готовность uncertain.')
evidence=[{'path':'inputs/evidence.md','locator':'C01/E09→SRC-0844 PDF physicalpp10–12; SRC-0853 Transcript13:12–14:01lines20–21,18:52–19:26lines30–31','depth':'frozen excerpts and structured package, primary source not reopened'},
          {'path':'inputs/evidence.md','locator':'C02/E10→PDF physicalp19; Transcript11:10–13:02lines16–19,29:58line52,41:50line79','depth':'frozen excerpts; no independent banking readiness claim'},
          {'path':'inputs/baseline.md','locator':'M05-2026-10-31; program rules and Q3 fund/issue interpretation','depth':'frozen package'},
          {'path':'inputs/context.md','locator':'Ограничения и одинаковые проверки; Нюансы','depth':'task requirements'},
          {'path':'supporting/finance-basis/basis.md','locator':'Балансы, резерв и годы2–3; Ресурсы вне закупочного лимита','depth':'scenario definitions, not bank evidence'}]
assumptions=[{'path':'supporting/finance-basis/scenario-inputs.json','locator':'common; fixed_C_cases_year; scenarios; actual_bank_inputs'},
             {'path':'checks/finance/source-manifest.json','locator':'exact real SHA256 and sealed references'},
             {'path':'checks/finance/model.py','locator':'explicit formulas and uncertainty; no author/sealed code executed'}]
paths=['checks/finance/'+x for x in ['model.py','write_report.py','verification.json','source-manifest.json','reused-annual.csv','reused-launch-annual.csv','reused-terminal-tail.csv','reused-dated-examples.csv','first15-verification.csv','personal-comparison.csv','positions-per-cycle.csv','finite-slot-bounds.csv','edge-cases.csv','concentration.json','resources.csv','launch-resources-monthly.csv','launch-resources-annual.csv']]
limits=('Не дан новый общий pass для fixed144/old35/price20/full-old. У30млн год1fail; '
        'квартальный пик FULL_NEW3466.667корзин (S1=2080>1800,S2=1386.667>1200), '
        'REGION80 S2=2133.333>1200, январскийпик/coldshop/×2труд не обеспечены обычными мощностями. '
        'Незапрошенный старый запас не объявлен полностью вновь фондированным; запрошенная старая очередь включена. '
        'Неполученное/U/условные права не экономия. Полный старый спрос — тяжёлый стресс, не обычный график.')
def finding(kind,text,loc):return {'classification':kind,'statement':text,'locator':loc}
common=[finding('calculation','24млнR=14.4lower+7.2top+2.4special. 7200×4×500 обеспечено всем подходящим; top250×7200×4 и special12×(32×2500+16×7500) — отдельные конечные пулы. Результат команды/benefitID не умножает сумму. Незанятые доли и округления остаются невыданными, не финансируют новые обещания.','checks/finance/model.py; personal-comparison.csv; edge-cases.csv'),
        finding('calculation','Вусловной области стационарный EXPECTED cash23.668млн+reserve7.372млн+buffer0.5=31.540млн год1. FULL_NEW cash31.040млн+buffer0.5; следующие стационарные FULL_NEW30.085/28.824млн, EXPECTED29.988/28.7464млн.','checks/finance/reused-annual.csv candidate_key=CON-011@v2,fixed_C_year=96000000'),
        finding('calculation','Prospective launch funding+buffer годы1/2/3=31.540/29.988/28.7464млн; FULL_NEW cash30.070/29.488/28.227млн, EXPECTED22.601/23.474/23.571млн. Первый год18.6млнposted+5.4млнconditional=24млн; четвёртые праваm13/14/15. Полный год2 сохранён, tail при stop-new m15/m36 закрываетсяm18/m39.','checks/finance/reused-launch-annual.csv; reused-terminal-tail.csv; source-manifest.json→../002/checks/finance/launch-monthly.csv'),
        finding('calculation_with_assumption','До14-го ordinarygross7.2млнR+special0.2млн, month-closeordinary5.4млн. При FULL_NEW m4 paidstock497933.33→109933.33RUB и netreserve937666.67 в обеих точках:388000RUB запаса текущей выплаты засчитаны один раз. Поздняяпоставка безпроверенной денежной замены fail, extra annual budget0. Actualдаты/SKU/деньгиunknown.','checks/finance/reused-dated-examples.csv; source-manifest.json→../002/checks/finance/date-prefunding-late.csv'),
        finding('calculation','Cclose=Copen+fixed+R→C−receivedC; Rclose=Ropen+posted−R→C−directR; Fclose=Fopen+grant−posted−unissuedexpiry; Uclose=Uopen+confirmed−posted. Конверсия1:1 и личный перевод не гасят права. Заказ не погашаетC до вручения. U учтено внутри обременённогоF одинраз. COLD_SHOP reserve содержит всю уже запрошенную очередь, включая старую часть; no_queuefail сохраняется.','checks/finance/model.py; verification.json; source-manifest.json→../002/checks/finance/monthly.csv,launch-monthly.csv'),
        finding('uncertain','Действительные источники/API/ACL, существующая QA и дополнительность труда, доступные часы/даты/региональные SKU/ценность, старые U/обеспечение неизвестны. ПервичнаяQA800ч/месяц×1500=14.4млнRUB/год требуемого ресурса; существующая/новаядоляunknown. ВторичнаяawardQA12ч сохранена отдельно; полезная производственная работа неизвестна и не принята за0.','supporting/finance-basis/scenario-inputs.json#/actual_bank_inputs; checks/finance/resources.csv'),
        finding('limits',limits,'checks/finance/reused-annual.csv; reused-launch-annual.csv; resources.csv; source-manifest.json→../002/checks/finance/monthly.csv')]
results=[]
for key in keys:
    x={'candidate_key':key,'scenario_scope':scope,'gates':{'budget':'fail' if key=='BASELINE' else 'pass','currency_balances':'pass'},'actual_readiness':{'budget':'uncertain','currency_balances':'uncertain','resources_and_dates':'uncertain'},'evidence_refs':evidence,'assumption_refs':assumptions.copy(),'findings':[],'calculation_paths':paths}
    if key=='BASELINE':
        x['scenario_scope']='Сценарная экстраполяция Q3×4:154.160млнRфонда,77.710364млнRвыдачи/год, не наблюдённый банковский год. '+scope
        x['findings']=[finding('calculation','Fixed96/full-new/old20 год1cash41.516млн+buffer0.5=42.016млнRUB>34млн. Годы2/3funding40.464/39.106млн; месячная физическая мощность такжеfail. EXPECTED cash34.144млн не заменяет потребность с резервом41.959811млн.','checks/finance/reused-annual.csv candidate_key=BASELINE,fixed_C_year=96000000'),finding('calculation','Из quarterlyF38.540млн выдано19.427591млн и закрыто только19.112409млнневыданного; личные начисленные/остатки не сгорают. C/R/F stock-flow проверены на тех же M05, включая старые личные200млн.','inputs/baseline.md#Фонд руководителя; checks/finance/model.py; verification.json'),finding('uncertain','Часы старой руководительской процедуры и реальный годовой объёмunknown; ресурс новойпроцедуры другим политикам не превращает этот неизвестный ресурс в0.','inputs/baseline.md; supporting/finance-basis/scenario-inputs.json#/actual_bank_inputs')]
    else:
        x['findings']=common.copy()
        if key=='CON-011@v2':
            x['artifact_consistency']='checked_current_money_and_hours'
            x['findings']+=[finding('calculation_and_uncertainty','Award4.284млнRUB/год; QA14.4млн отдельно; всего18.684млн. Launchyear1award+startup6.7652млн,QA10.8млн,всего17.5652млн. HRcommon151.111+own60=211.111≤220; exportfallback231.111>220. Fullsourcecreation+no-reusableQA48.564млн/год. Это ресурс, не фактическая допкасса.','checks/finance/resources.csv; launch-resources-annual.csv')]
        if key=='CON-011@v3':
            x['artifact_consistency']='checked_money_and_hours; operational_savings_assumption_unverified'
            x['assumption_refs']+=[{'path':'branches/A/assumptions-011.csv','locator':'A20–A26; B05/B07/B13/B19'}]
            x['findings']+=[finding('hypothesis_and_calculation','10HRмин/группа разложены на8повторнойсборки+2контроля: новое проектное допущение, не выявленный факт. Удаление8мин×60групп=8HRч/месяц; +2ITч/месяц даёт6ч и4000RUB экономии/месяц. Не меняются QA800/secondary12/первичныйsourcecapture/independentsigners/posting. Все445примеров и15месячные денежныеячейки неизменны.','branches/A/finance-spec-011.json#/workload/new_procedure; checks/finance/verification.json'),finding('calculation','Award4.236млнRUB/год (−48000); QA14.4млн отдельно,вместе18.636млн. Upfront+24IT+4HR+4manager=58000RUB; вlaunchyear1 экономится72HRч, добавляется24ITч: net+34000RUB; launchaward+startup6.7992млн,QA10.8млн,вместе17.5992млн. Суммарно за первый год сэкономлено16ч, но это не кассовая экономия.','checks/finance/resources.csv; launch-resources-monthly.csv; launch-resources-annual.csv'),finding('calculation_and_uncertainty','HRcommon151.111+52=203.111≤220; export/fullsourcefallback223.111>220fail; nominal launchpeak205.511/export225.511. Fullsourcecreation+no-reusableQA48.516млн/год, при×2 и пике всехобращений HRfail. Положительный стационарный ресурс требует реальноустранимыхduplicate>4мин/группа; возможные8мин недостаточныдляHR220fallback(нужно11.111).','checks/finance/resources.csv; first15-verification.csv; branches/A/time-sensitivity.json')]
        if key=='CON-015@v1':
            x['artifact_consistency']='one_open_prose_arithmetic_typo; financial_spec_and_calculated_envelope_consistent'
            x['assumption_refs']+=[{'path':'branches/B/assumptions-015.csv','locator':'T01–T04; B05/B07/B13/B19'}]
            x['findings']+=[finding('calculation','40/30/20/10 приn40=4000/3000/2000/1000R; 8команд5делятна800/600/400/200лично. 4вместо2оплаченныхединиц;40индивидуальныхдают4вместо2людей,команды20вместо10людей/цикл. 180группдают720вместо360позиций/цикл, не уникальных людей/год. Доляпервыхв24млн=12%вместо24%; first-to-lower8вместо16 уиндивида и1.6вместо3.2 уравногоучастникакоманды.','checks/finance/personal-comparison.csv; positions-per-cycle.csv; concentration.json'),finding('calculation','Дваквалифицировавшихсяиспользуют70%P; одинпри40зарегистрированных40%P; одинзарегистрированныйtop0. Массоваяничья40людей/8команд5сохраняет250Rлично. Ничья4–6=333каждому,1Rневыдан; FTE/непрошедшаядоля/округлениенеперенормируются. КрайниймалыйFTEможетдать0, полезныйSKU/ценностьнепроверены. Вавторскихn10/n100ranked есть совпадения округлённыхQ; их оплаченные2496/24996Rкорректны, отличаяоттеоретическихразныхрангов2500/25000.','checks/finance/edge-cases.csv; finite-slot-bounds.csv; verification.json'),finding('calculation','IT+1ч/месяц=24000RUB/год; award4.308млн,QA14.4млн,всего18.708млн. Upfront58000RUB, launchyear1дельта82000RUB, award+startup6.8472млн,QA10.8млн,вместе17.6472млн. HRпроцедура60чнеизменна:211.111≤220,export231.111>220; fullsource+noQA48.588млн/год.','checks/finance/resources.csv; launch-resources-annual.csv'),finding('open_prose_arithmetic_issue','Вconcept-015.mdстр45написано42500Rобычногопризнания/год. Верно4×(10000+500)=42000; +15000special=57000какправильноуказановтекстедалее. Сохранённыйcap97000nonbinding; issueнеизменяет24млнпотолок/календарь,но42500нельзякопироватьвматериалы. Авторскийфайлнеизменён.','branches/B/concept-015.md:45; checks/finance/concentration.json')]
    results.append(x)
write(R/'checks/finance.json',{'schema_version':1,'classification':'independent targeted scenario check; no selection or ranking','results':results,'verification':'checks/finance/verification.json','source_hashes':'checks/finance/source-manifest.json','money_core_reuse':{'lawful':True,'scope':'same E24 aggregate flows/calendars only; independent source SHA and current invariants verified','labor_and_personal_recomputed':True,'not_inherited':['new candidate gates','new labor','personal top payouts','bank readiness']},'open_findings':[{'candidate_key':'CON-015@v1','issue':'prose42500 should42000 ordinary/year','locator':'branches/B/concept-015.md:45','impact':'isolated prose discrepancy, not envelope/balance violation'}]})
report='''Три политики с максимумом 24 млн R проходят бюджетный gate **только в условной области M05: fixed96 / old20 / базовые цены / 34 млн ₽**. Валютные балансы проходят проверку. У BASELINE Q3×4 бюджетный gate — fail. Фактическая готовность банка остаётся uncertain. [Контракт всех четырёх ключей](finance.json), [формулы](finance/model.py), [проверка](finance/verification.json), [SHA и locators](finance/source-manifest.json).

| Политика | Максимум, млн R/год | Год 1 FULL_NEW с резервом и буфером, млн ₽ | 30 / 34 млн ₽ |
|---|---:|---:|---|
| BASELINE, сценарий Q3×4 |77,710364|42,016|fail / fail|
| CON-011@v2 |24|31,540|fail / pass|
| CON-011@v3 |24|31,540|fail / pass|
| CON-015@v1 |24|31,540|fail / pass|

Общие допущения: старые личные 160 млн C + 40 млн R; их предъявление 20%/год; fixed96 млн C/год при прежних ставках; новые fixed/R предъявлены полностью. Корзина 5000 C стоит 940 ₽ закупки + 30 ₽ доставки. Регионы 60/40, мощности 1800/1200 корзин в месяц; партии 100, предзаказ на месяц; начальный склад и резерв — 0. EXPECTED использует 60% новых fixed отдельно. Бюджет 30–34 млн ₽ на закупки — факт кейса: inputs/evidence.md C02 → PDF физ. с.19; труд/IT отдельно. Первичные источники заново не открывались, использован замороженный пакет.

24 млн R = 14,4 нижний уровень + 7,2 top + 2,4 special. Гарантия 7200×4×500 обеспечена полностью. Команда делит один приз; незанятые слоты и округления не финансируют новые обещания. EXPECTED год 1: касса 23,668 + резерв 7,372 + буфер 0,5 = 31,540 млн ₽. Накопленные остатки остаются обязательствами спроса. Конверсия 1:1 и перевод не гасят права; заказ погашает C при вручении. F, условное обещание, U и личные остатки разделены; U внутри обременённого F учтено один раз.

Пять входов, M05, потолок, календарь и реальные SHA совпали с проверенным денежным core. Его CSV переиспользованы законно; авторские и закрытые скрипты не запускались. Личные выплаты и труд пересчитаны независимо, сетка сценариев не расширялась. [Годовые деньги](finance/reused-annual.csv), [запуск и полный год 2](finance/reused-launch-annual.csv), [первые 15 месяцев](finance/first15-verification.csv).

В запуске обычные права возникают с m4, четвёртые окна закрываются m13/m14/m15. В год 1 проведено 18,6 млн R, ещё 5,4 млн условных обещаний сохраняются. Финансирование с буфером за годы 1/2/3: 31,540 / 29,988 / 28,7464 млн ₽; FULL_NEW касса: 30,070 / 29,488 / 28,227. Стационарный FULL_NEW за годы 2/3: 30,085 / 28,824 млн ₽. При остановке новых обещаний после m15/m36 [хвост](finance/reused-terminal-tail.csv) закрывается m18/m39.

До 14-го gross ordinary достигает 7,2 млн R плюс special 0,2 млн; 5,4 млн — только остаток на конец месяца. Нужен пригодный оплаченный склад, выделенный один раз до нового усилия, либо проверенная ликвидная замена. В m4 FULL_NEW склад 497933,33 → 109933,33 ₽; резерв в обеих точках 937666,67 ₽. Разница 388000 ₽ не считается второй раз. Поздняя поставка без денежной замены — fail графика, дополнительный годовой бюджет не возникает. [Датированные примеры](finance/reused-dated-examples.csv); полный late-check указан в manifest. Реальные даты/SKU неизвестны. Cold shop сохраняет всю запрошенную старую/новую очередь в резерве и no_queue fail.

CON-011@v3 сохраняет все 445 личных примеров и денежные ячейки. Деление прежних 10 HR-минут на 8 минут повторной сборки + 2 минуты контроля — новое допущение. При 60 группах: −8 HR-часов и +2 IT-часа в месяц. Дополнительная подготовка 24 IT + 4 HR + 4 manager стоит 58000 ₽. Первый год требует **на 34000 ₽ больше ресурса**; затем экономия **48000 ₽/год**. Для положительной стационарной экономии нужно реально устранять более 4 минут на группу. QA800, вторичная проверка12 и создание источника сохранены. Export fallback: 223,111 > 220 HR-часов — fail; запусковый пик 205,511, с fallback 225,511 часа.

CON-015@v1 при n40 платит 4000/3000/2000/1000 R; в восьми равных командах по пять — 800/600/400/200 участнику. Четыре позиции вместо двух дают 4 вместо 2 личных получателей в индивидуальной группе и 20 вместо 10 в командах за цикл. 720 вместо 360 позиций при 180 группах — не число уникальных получателей за год. Доля первых позиций во всём фонде снижается с 24% до 12%. Два квалифицировавшихся используют 70% пула; массовая ничья оставляет прежние 250 R каждому. Ничья мест 4–6 даёт 333 R, остаток 1 R невыдан. FTE может округлить личную долю до 0; полезный малый SKU и ценность не подтверждены. [Личные суммы](finance/personal-comparison.csv), [позиции за цикл](finance/positions-per-cycle.csv), [ничьи/FTE](finance/edge-cases.csv), [малые n без ничьих](finance/finite-slot-bounds.csv).

В concept-015.md:45 есть опечатка: обычный максимум **42000 = 4×(10000+500)**, написано 42500. Общий максимум со special 57000 указан верно; cap97000 сохранён и не связывает выплаты. Потолок 24 млн и валютный баланс не затронуты. Авторский файл не изменён. В дополнительных n10/n100 fixtures есть совпадения округлённых Q: выплата 2496/24996 корректна, теоретические разные ранги дают 2500/25000.

| Ресурс вне закупок, млн ₽ | CON-011@v2 | CON-011@v3 | CON-015@v1 |
|---|---:|---:|---:|
| Стационарная award-процедура |4,284|4,236|4,308|
| Первичная QA всего |14,400|14,400|14,400|
| QA + award |18,684|18,636|18,708|
| Запуск, год 1: award + подготовка |6,7652|6,7992|6,8472|
| Запуск, год 1: QA + award + подготовка |17,5652|17,5992|17,6472|
| Полное создание источника + отсутствие reusable QA, год |48,564|48,516|48,588|
| HR общие + собственные, ч/месяц |211,111|203,111|211,111|
| HR с export fallback, ч/месяц |231,111|223,111|231,111|

Ставки M05: HR1000, manager1500, employee1000, IT2000 ₽/час. QA800 оценена один раз; существующая и новая доли неизвестны. Вторичная award-проверка12 часов отдельно. Полное создание источника добавляет 1300 employee + 700 manager часов к export20HR+80manager; формулы сохранены. Общие корзинные часы и 6 минут сотрудника на заказ добавляются отдельно один раз. [Ресурсы](finance/resources.csv) разделяют обычный режим, export, полное создание источника, пик всех обращений, ×2, гипотетическую 25% кассу замещения и actual unknown. 20% общей HR-допкассы — отдельный параметр. [Труд по месяцам](finance/launch-resources-monthly.csv), [полные годы](finance/launch-resources-annual.csv). B добавляет 1 IT-час/месяц и 58000 ₽ подготовки: +82000 ₽ ресурса в первый год. Производственная работа и её дополнительность неизвестны.

Прямой R-сервис погашает те же R вместо каталога. При допущениях 20000 R / 8 часов / 1000 ₽ и 25% кассы новые 24 млн R дают 9600 часов, 9,6 млн ₽ ресурса / 2,4 млн ₽ кассы вне закупок. Эти R исключаются из физических заказов; резерв каталога не оплачивает услугу повторно. Реальные условия сервиса неизвестны.

Ограничения сохранены: fixed144, old35, price20 и полный старый спрос не получили нового общего pass34млн. Квартальный FULL_NEW пик 3466,667 корзин и REGION80 в S2 2133,333 превышают обычную ёмкость; январский пик, cold shop и ×2 труда остаются ограничениями. При всех 7200 special/2400 апелляциях HR также fail. Полное старое предъявление — тяжёлый стресс, не обычный график. Фактические остатки/U/обеспечение/минуты/источники/ACL/часы/каталог/даты/эффект uncertain; арифметика и синтетика не доказывают готовность банка.
'''
(R/'checks/finance.md').write_text(report)
# Same standalone report; all links made relative to finance/ for packet assembly.
review=report.replace('(finance/','(').replace('(finance.json)','(../finance.json)')
(P/'finance-for-review.md').write_text(review)
print('finance.json: 4 keys; reports written; open prose issue recorded')
