from pathlib import Path
import csv,json,hashlib

H=Path(__file__).resolve().parent;R=H.parent.parent
A=json.loads((R/'branches/A/finance-spec.json').read_text());AK=A['candidate_key']
def rows(n):return list(csv.DictReader((H/n).open()))
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def m(v):return f'{float(v)/1e6:.3f}'
annual=rows('structural-annual.csv');profiles=rows('employee-paths-comparable.csv')
def pick(E,sc='FULL_NEW',fixed=96_000_000,y=1,key=None):
    return next(r for r in annual if r['candidate_key']==(key or AK) and int(r['available_R_year'])==E and r['scenario']==sc and int(r['fixed_C_year'])==fixed and int(r['year'])==y)
table='| fixed, млнC/год | Сценарий | E24, млнруб. | E36, млнруб. |\n|---:|---|---:|---:|\n'
for fixed,sc,label in [(96e6,'EXPECTED','ожидаемый спрос + резерв'),(96e6,'FULL_NEW','все новые права'),(144e6,'EXPECTED','ожидаемый спрос + резерв'),(144e6,'FULL_NEW','все новые права'),(96e6,'FULL_NEW_OLD35','старое предъявление35%'),(96e6,'FULL_NEW_PRICE20','цены закупок+20%')]:
    table+=f'|{int(fixed/1e6)}|{label}|{m(pick(24_000_000,sc,int(fixed))["cash_reserve_buffer_RUB"])}|{m(pick(36_000_000,sc,int(fixed))["cash_reserve_buffer_RUB"])}|\n'
pt='| Профиль | '+AK+' R/год | CON-017@v1 R/год | CON-015@v1 R/год | Первый500руб. безfixed: A / B / C | С указаннымиfixed: A / B / C |\n|---|---:|---:|---:|---|---|\n'
names={'ordinary_no_top':'Обычный, безtop','strong_repeat_winner':'Первое место каждый цикл','novice':'Новичок с началаT0, безtop','team_member':'1/5 первой команды','part_time':'0,5FTE, нормальный уровень','restricted_region':'Регион, безtop'}
for profile,label in names.items():
    rr=[];without=[];withfixed=[]
    for key in [AK,'CON-017@v1','CON-015@v1']:
        x=next(r for r in profiles if r['candidate_key']==key and r['available_E_R_year']=='24000000' and r['profile']==profile and r['corporate_case']=='none');rr.append(str(int(float(x['R_per_completed_12_observation_months']))));without.append('m'+x['first_2500C_500RUB_month'] if x['first_2500C_500RUB_month'] else 'нет')
        x=next(r for r in profiles if r['candidate_key']==key and r['available_E_R_year']=='24000000' and r['profile']==profile and r['corporate_case']=='specified_events');withfixed.append('m'+x['first_2500C_500RUB_month'] if x['first_2500C_500RUB_month'] else 'нет')
    pt+='|'+label+'|'+'|'.join(rr)+'|'+' / '.join(without)+'|'+' / '.join(withfixed)+'|\n'

neutral=f'''# Сопоставимая финансовая проверка

31.10.2026. Все суммы — сценарные расчёты по M05. Это проверка проекта, не отчётность ОТП, не подтверждение закупочной готовности и не оценка мотивационного эффекта. Проверены {AK}, CON-017@v1, CON-015@v1 и BASELINE. Полезность300/500/1000руб. — проектные гипотезы. Бюджет30/34млнруб. относится к закупкам; труд/IT/замещение показаны отдельно.

## Границы допуска

У всех четырёх есть **условный финансовыйpass для нормированного E24 при fixed96млнC, старом предъявлении20%, базовых ценах, закупочном лимите34млнруб. и выполненных предварительных условиях обеспечения**. Для BASELINE это контроль полного использования равного конверта, а не новый личный регламент. Мощности, данные, оплаченный пригодный запас/деньги до усилия и независимый труд должны действительно существовать. Реальная готовность банка неизвестна.

Этотpass не распространяется на30млнруб., fixed144, старое предъявление35%, цены+20%, холодный магазин, тяжёлые региональные/квартальные пики или отсутствующий источник/необеспеченный труд. E36 имеет отдельные ограничения ниже. Невыполнение обязательного предварительного условия означает, что обещание нельзя открывать; уже заработанное, U и заказы сохраняются.

## Равная экономика масштаба

Год1: требуемая закупочная касса + изменение резерва всех новых непогашенных прав + буфер0,5млнруб. Сохранены все fixed и старые личные права, склад засчитан ровно один раз. В таблице один и тот же E для обеих новых механик; различия выплат не объявляются различием стоимости единицы.

{table}

При full-new/fixed96/old20 E24 требует по годам1/2/3 **{', '.join(m(pick(24_000_000,y=y)['cash_reserve_buffer_RUB']) for y in [1,2,3])}млнруб.**; E36 — **{', '.join(m(pick(36_000_000,y=y)['cash_reserve_buffer_RUB']) for y in [1,2,3])}млнруб.**. Это общий консервативный годовой контроль полной интенсивности, не календарная касса первого запуска. Ожидаемый спрос не отменяет резерва: например expected/fixed96/E24 касса23,668млнруб., но с резервом/буфером31,540млнруб.

CON-015@v1 назначает ставки и максимум24млнR при доступном конверте36:12млнR остаются нераспределёнными. Масштабированная версия не подменяет её в сравнении. BASELINE при24/36 — нормирование полного дополнительного конверта без изобретения личных выплат. Отдельная экстраполяция Q3×4: фонд154,160млнR, выдача77,710364млнR, невыданные76,449636млнR. Это арифметическое повторение одного квартала, не факт года. При таком R-выходе full-new/fixed96/old20 требуется42,016млнруб. с буфером — fail34. Сокращение конверта относительно этой экстраполяции нельзя приписывать механике признания.

## Конкретная награда и закупка

Проектный ценник5C/руб. номинала и R→C1:1 дают:300руб.=1500C/R,500руб.=2500,1000руб.=5000. Это не фиксированный банковский курс и не обналичивание. 5000C в M05 — единица смешанной корзины, а не минимальная цена магазина.

M05mix0,194руб./C — средняя80%сертификатов/20%мерча с логистикой. Конкретный сертификат500руб. при закупке100%номинала стоит500руб. до неизвестных комиссий. Если весь новыйR погашается сертификатами, а fixed/старое остаются M05mix, надбавка144/216тысруб. дляE24/E36. Общий full-new/fixed96/old20 год1 становится **31,684/34,181млнруб.** до комиссии: E24 проходит34, E36 уже нет. Комиссия5% даёт31,924/34,541;10% —32,164/34,901млнруб. Это чувствительность, не котировка поставщика. Если сертификатами погашается только гарантия18млнR, её премия к смеси108тысруб.; единичная сертификатная цена не заменяется средней.

Нет доказанной универсальной адресной пригодности бренда/доставки/наличия в ОТП. Баланс, заказ и вручение — разные состояния. Лимит «не более3» на PDF8 имеет неизвестный период/охват: достижение достаточного баланса не означает право немедленно купить любое число сертификатов. Первый500/1000руб. в примерах требует одного подходящего сертификата, но его обеспечение остаётся условием.

## Сколько стоит содержательная гарантия

| Гарантия всем7200 | МаксимумR/год | Сертификатная стоимость погашения/обеспечения, млнруб. | Остаток E24 / E36, млнR |
|---|---:|---:|---:|
|500R каждый квартал|14,4млн|2,88|9,6 /21,6|
|1500R дважды/год|21,6млн|4,32|2,4 /14,4|
|2500R ежегодно|18млн|3,6|6 /18|
|2500R дважды/год|36млн|7,2|−12 /0|
|5000R ежегодно|36млн|7,2|−12 /0|

Первая строка — контроль, не утверждение содержательности500R. Гарантия не рассчитывается на небольшой ожидаемый процент успешных: все7200 включены. Суммы сертификатной закупки здесь только за гарантию, поверх fixed/старого и без сервиса. При2500R ежегодно остаётся6млнR E24 дляtop/special. В {AK} это4,32/1,68; цена охвата — меньшие призы сильным. Два500руб.-права в год всем требуют36млнR **до** конкурса. С сохранением6млнR на другие каналы нужно42млнR; с сохранением25%фонда на них —48млнR. Уже аналитическая M05граница до партий дляfixed96/old20 требует35,032/36,196млнруб. соответственно, поэтому34 не хватает; сертификатная премия/комиссии увеличивают разрыв. При36млнR только на гарантию внутренний конверт сходится, но контроль сертификатной закупки выше также не проходит34. Нельзя решить это скрытым отбором меньшего числа подходящих или сокращением fixed.

## Календарь, условные обещания и резерв

{AK}: девять заранее назначенных когорт по800, фиксированное полугодовое квалификационное окно один раз в12месяцев. Каждый из7200 имеет ту же гарантию2500R(E24)/3750R(E36); оба квартала должны пройти Q/QA/экспозицию. Первая валютаm7–15, последующие даты через12месяцев; до8месяцев ожидания начала поздней когорты. Неуспех даёт0G в этом окне; следующая попытка только в следующем годовом окне. Это цена фиксированного календаря, особенно для неполной экспозиции и новичка после начала окна: пример C1hirem4 не получаетGm7, возможноеGm19,15месяцев с прихода. Общий профиль новичкаT0m1 успевает в первое окно.

E24 кm12:15,84млнR проведено +7,08млн открытых условных обещаний +1,08млн ещё не открытых плановых разрешений =24млн. Эти категории не сливаются: последнее не заработанное право. CON-017@v1:19млн проведено +5млн открытых обещаний/U; CON-015@v1:18,6+5,4. Меньшая ранняя касса не является экономией или доказательством полного допуска30млнруб. Последние объявленные окна всех текущих правил закрываютсяm39; доказанныеU/заказы/личные остатки могут сохраняться дальше без списания. Fixed в хвосте не отменяются.

У {AK} годовой максимум гарантии18млнR не добавляется повторно к уже включённым в него открытым окнам. На месячной сетке максимальный gross до quality-close с новым объявлением составляет15,58млнR приE24/23,37приE36, включая14/21млн гарантийных открытых окон, top-overlap иspecial. Консервативная общая граница N×G +top-overlap+special —19,58/29,37млнR; это альтернативная верхняя граница, не дополнительный второй резерв. У CON-017@v1 gross6,5/9,75млнR; у CON-015@v1 —7,4млнR. Все они **дополнительно** требуют сохранённого обеспечения личных C/R, fixed, подтверждённыхU и старых заказов. Пригодный оплаченный склад учитывается один раз; остаток экспозиции покрывается отдельными доступными деньгами до усилия14-го/1-го. Реальное наличие/переносимость средств неизвестны.

## Мощности и малыеSKU

M05 full-new/fixed96/old20, верхний all-qualifying календарь:

| Вариант/фонд | Пик5000C-эквивалентов/месяц | HRобщий+recognition, ч/месяц | Условные3000/220 |
|---|---:|---:|---|
|{AK},24|2766,667|217,778|pass|
|{AK},36|3016,667|224,444|fail|
|CON-017@v1,24|2666,667|211,111|pass|
|CON-017@v1,36|2866,667|216,444|pass дляM05mix; сертификатная кассаfail34|
|CON-015@v1,24 или доступный36|2666,667|211,111|pass длянеизменных24|

Отказы качества в фиксированных окнах уменьшают выдачу, не переносят её на другую дату. Сбой банка/поздняя верификация всё равно требуют сохраненияU и отдельной проверки инцидентной мощности/SLA. Ручной exportfallback добавляет20HRч/месяц и не проходит220 даже приE24; отсутствие источника сверх этого требует700manager+1300employeeч/месяц. Удвоение труда не проходит доступный ресурс автоматически. При80%спроса во втором регионе, квартальном синхронном погашении или январском старом пике годовогоpass недостаточно. Безm0предзаказа холодный магазин не исполняетm1; вся старая и новая запрошенная очередь остаётся обязательной, не становится экономией.

**Единицы нельзя смешивать.** E24 в сертификатах500руб./2500C —9600 новых транзакций/год вместо4800 условных5000C-корзин; E36 —14400 вместо7200. При500руб.-SKU на пике {AK}/E24 получается3266,667 гибридных транзакций и224,444HRч, если оставшийся fixed/старый поток сохраняет M05proxy; CON-017@v1/CON-015@v1 приE24 —3066,667 и216,444ч. Здесь новая сертификатная обработка заменяет прежнюю смешанную, не начисляется второй раз. Если условно перенести лимит3000 именно на заказы, он не проходит. Однако это **отдельная чувствительность единицы мощности**, не установленный факт банковского лимита цифровых кодов. Реальная пакетная выдача/числоSKU/минуты/региональная цифровая мощность неизвестны. Модельныйpass объёма не доказывает массовую выдачу500руб.-кодов; неизвестность одинаково раскрыта для всех.

## Одинаковые личные пути

Все старые остатки0, одна группа40, сильный — первое место каждый допустимый цикл, командный пример —8команд×5 и1/5первого приза. ГодR — четыре завершённых квартала/один квалификационный год, не календарныеm1–12. Случайные корпоративные события не приписываются рабочему достижению. Вторая версия пути использует только фактически случившиеся150Cкурсm1+50опросm2+50birthdaym6+1000стажm12=1250C; новичок1050C первого года без стажевой1000, с реально пройденным испытанием/входом/eNPS. Ни все активности, ни благодарности других не предполагаются. Самосообщение факта не равно самоодобрению: источники/QA/проводка подтверждаются другими; top дополнительно зависит от места, special — от факта, другого подтверждающего и свободного конечного слота.

{pt}

Месяцы — достижение достаточного баланса после независимой проводки, каждый номинал считается отдельным путём без предыдущих покупок. **Фактическое получение может быть позже** при неподходящемSKU/адресе/сбое; региональный профиль нельзя объявлять обеспеченным одним электронным кодом. Для первой малой300руб. безfixed обычному нужныm7 в{AK},m10 вCON-015@v1; CON-017@v1 не даёт новогоR. У новичка с1050C квартальная500Rвыплата позволяет300руб. ужеm4, а {AK} —m7: крупная первая награда не улучшает каждый меньший ориентир. В CON-017@v1 отдельно выполненное внедрённое достижение со свободным5000Rслотом может дать1000руб. с первой награды, но это не назначено обычномуQ1/no-topпрофилю.

Фазирование также важно. Безfixed обычный получает500руб. вm7–15 у{AK},m16–18 уCON-015@v1. С указаннымиfixed CON-015@v1 достигает500руб. вm12 во всех трёх когортных датах; поздние когорты{AK} —m13–15. Поэтому улучшение не всеобщее, особенно при реальном корпоративном начислении раньше гарантии. ПриE36 годовыеR обычного/сильного/командного в{AK} —3750/18150/6630, вCON-017@v1 —0/60000/12000. CON-015@v1 остаётся2000/18000/5200 при доступном36. Полные72основных и360когортных строк — вCSV; минимальная экспозиция не превращается в FTE-срез ставки, но её отсутствие может лишить текущего fixedwindow.

## Труд и альтернативные награды

Стационарный recognition-ресурс вне закупок: {AK}4,404млнруб./год; CON-017@v1 приE24/36 —4,3485/4,4235; CON-015@v1 —4,308. Разовая подготовка3,322/3,264/3,222млнруб. соответственно. Это стоимость требуемого времени, не доказанная новая касса. ПервичнаяQA800ч/месяц=14,4млнруб./год показана отдельно и ровно один раз; её существующая/новая доля неизвестна. ОбщийshopHR при полном равномерномE24 —1,813333млнруб. ресурса/год,20%допкассы в M05 —0,362667млн; не включается повторно в recognition. У BASELINE труд назначения/одобрения не известен, не принят нулём.

Сохранены×2всегоrecognition/QA и25%оплачиваемого замещения. Например {AK}QA+recognition18,804млнруб. ресурса, при×2 —37,608; если всё было бы дополнительным,25%замещения4,701млнруб.кассы. Это отдельные сценарии, не прибавление всех альтернатив одновременно. Работа над полезным результатом и создание доказательств не считаются бесплатными внутри нескольких минут верификации.

ПрямойR-сервис — альтернативное погашение тех жеR, исключаемое из физического заказа. M05условие20000R/8ч: E24=1200сервисов/9600ч/9,6млнруб.ресурса и2,4млнруб. дополнительной кассы; E36=1800/14400ч/14,4/3,6. Это не бесплатный способ вписать сертификатную гарантию, нужны мощность/замещение; существующиеR-возможности сохраняются.

## Проверки и ограничения

Расчёт `calculate.py` читает JSON как данные, не импортирует/не исполняет авторские калькуляторы или M05script. 648структурных годовых строк воспроизведены с максимальным отклонением от готовой провереннойM05таблицы3,73e−8руб. Месячныйбаланс C/R, конверсия1:1, склад/касса/резерв иF-границы сверены; CSV-only`verify.py` отдельно проверяет инварианты, личные сроки, труд и conditionalокна. SHA входов сохранены. Непогашенный личный запас, очередь и U не сгорают при конце модели.

Базовыефакты: PDF10–12/14–15/19 через frozen`inputs/evidence.md` C01–08; M05`supporting/finance-basis/scenario-inputs.json` иbasis.md; SKUи ограничения `supporting/reward-basis.md`/reward-sources.json. Цены/частоты/состав/7200/мощности/часы — раскрытые проектные предположения. Проверка не доказывает фактические данные, снабжениедо14-го, независимость банковских прав доступа, адресную полезность, доступный труд или мотивационный эффект. Выбор рекомендации не относится к этой финансовой проверке.
'''
(H/'finance-for-review.md').write_text(neutral)
history='''\n## Проверка единственного целевого исправления\n\nПервичная CON-016@v1 разрешала плавающий повтор после неудачных кварталов. Собственный fixture трёх когорт1/4/7 вm13 дал6,5млнR,3433,333корзины,235,556HRч иfail3000/220 (уменьшение старого запаса после первого года учтено). Первичные результаты/калькулятор/SHA сохранены в `checks/finance/initial/`; там также зафиксировано противоречие250*n вteam_rule. CON-016@v2 проверена как отдельная версия: размеры/9когорт/QA/общаяM05сохранены, фиксированные окна убрали плавающую дату; любое качествоfail уменьшаетпоток, а не сдвигаетего. Team_rule согласован с150/225. Хвост стал39, потерявшийокно сотрудник/позднийновичок ждётследующийгод. Новая цена недоступности не названа бесспорным улучшением. Промежуточныйall-goodpassv1неиспользованкакобщаягарантия; финальныеchecks относятсятолькокv2. История исправления не входит в назначенный reviewer текст.\n'''
(R/'checks/finance.md').write_text(neutral+history)

common_paths=['checks/finance/calculate.py','checks/finance/verify.py','checks/finance/verification.json','checks/finance/independent-verification.json','checks/finance/structural-annual.csv','checks/finance/structural-monthly.csv','checks/finance/calendar-annual.csv','checks/finance/calendar-monthly.csv','checks/finance/calendar-peaks.csv','checks/finance/certificate-sensitivity.csv','checks/finance/employee-paths-comparable.csv','checks/finance/employee-paths-cohort-sensitivity.csv','checks/finance/guarantee-frontier.csv','checks/finance/dated-prefunding.csv','checks/finance/fixed-window-conditional-ledger.csv','checks/finance/small-sku-orders.csv','checks/finance/small-sku-monthly-sensitivity.csv','checks/finance/resources.csv','checks/finance/baseline-F-controls.csv','checks/finance/cold-shop-queue.csv','checks/finance/virtual-alternative.csv','checks/finance/finance-for-review.md']
scope='M05 conditional prototype admission: E24, fixed96mC/year, old20%, base prices,34mRUB purchase limit, all new promises backed; m0forecast/prepaid suitable stock or segregated cash before effort, independent labor/data available. 30m/fixed144/old35/+20%price/heavy peaks/cold shop/missing source not passed. Actual bank readiness unknown.'
findings={
 AK:['All7200 guarantee ceiling18mR atE24, no expected-success discount; total18+4.32+1.68=24mR. E36:27+6.48+2.52=36mR.','Fixed6month annual windows: maximum all-good monthly2.5mR(E24),2766.667M05basket equivalents,217.778HRh; E36 3016.667/224.444 fail. Failure onlyreduces current window award; next chanceannual.','Ordinary2500R/year vs2000 in exact quarterly500 design; first500RUB C1m7, phasesm7..15. Strong12100/team4420 Ryear; gains are not universal with corporate events or later hire.','Gross actual conditionalpeak15.58mR atE24; globalN*G18m is a ceiling including the guarantee offers, not an added duplicate. ExistingU/orders/fixed/old add separately; real backing unknown.','Fullnew certificate sensitivity31.684mRUB E24 pass34,34.181m E36 fail34. SmallSKUtransaction capacity distinct/unverified; conditionalsame-order sensitivityfails, not a claimedbanklimit.'],
 'CON-017@v1':['E24=18mRtop+6machievement;E36=27+9. No universal extra right; ordinaryQ1/no-top/no-special gets0R.','Upper monthlyE24/E36 2m/3mR; allgoodM05basket/HRpass withinfixed96/old20. E36certificates34.181mRUB fail34 despite mixedcost33.965pass.','First individual top10000R atE24 can buy1000RUB fromfirstpostm4; teamone-fifth2000R first500RUBm7. Finite slots/ties/repeated winners can reduce coverage and personal nominal; no average allocation substituted.','m12posted19mR+open5m;grossbeforeoldqualityclose6.5mR,9.75m atE36;Uandorderspreserved.'],
 'CON-015@v1':['Rules issue24mR/year; available36 leaves12mR unallocated. A scaled projection is a distinct mechanic and is not used as this candidate.','Ordinary500R/quarter=2000R over4cycles; fromzero andno fixed300RUBm10/500RUBm16. Specifiedactual1250C gives500RUBm12; novice1050C gives300RUBm4/500RUBm10.','m12posted18.6mR+open5.4m; gross7.4mR. E24M05upper2666.667basket/211.111HRh; coldshop/old35/fixed144/pricestress/fallback not passed.'],
 'BASELINE':['Same24/36 envelopes are fullutilizationcomparison scenarios, not knowncurrentallocation or inventedindividualguarantee. Personal discretionaryRpathunknown.','SeparateQ3x4extrapolation:154.16mRgrants,77.710364mRposted,76.449636mRunissuedexpiry. Fullnewfixed96/old20year142.016mRUBfail34, not observedannualcost.','C/R conversion-neutral balances and separateFexpiry control preserved. Existingadmin/awardlaborunknown, notzero; oldpersonalandordersretained.']}
results=[]
for key in [AK,'CON-017@v1','CON-015@v1','BASELINE']:
 results.append(dict(candidate_key=key,scenario_scope=scope,gates={'budget':'pass','currency_balances':'pass'},evidence_refs=['inputs/evidence.md#C01-C08','supporting/finance-basis/basis.md','supporting/reward-basis.md'],assumption_refs=['supporting/finance-basis/scenario-inputs.json#/common','inputs/context.md','supporting/employee-profiles.md'],findings=findings[key],calculation_paths=common_paths))
save(R/'checks/finance.json',{'schema_version':1,'scope_note':'Pass is scoped to the stated common E24/34m scenario, not actual bank deployment or all sensitivity cases. No winner selected.','results':results})
initial=json.loads((H/'initial/verification.json').read_text());final=json.loads((H/'verification.json').read_text())
save(H/'delta-verification.json',{'initial_candidate':'CON-016@v1','final_candidate':AK,'initial_verification':'checks/finance/initial/verification.json','initial_failure':'checks/finance/initial/finding.md','final_verification':'checks/finance/verification.json','initial_source_sha256':initial['source_sha256'],'final_source_sha256':final['source_sha256'],'fixed_parameters_unchanged':['N7200','9cohorts800','E24/E36G2500/3750','top150/225','specialfund','Q/QA','fixed/old/budget/M05'],'mechanism_delta':'Fixed halfyear annual qualification window; no floating retry. Tail39. Missing current window has nextannualchance; laterhireexamplem4->m19 explicit.','final_allqualifying_monthly_ceiling_verified':True,'final_budget_scope':scope,'no_second_rework_requested':True})
print(json.dumps({'current_candidates':[r['candidate_key'] for r in results],'finance_json':'checks/finance.json','review_text':'checks/finance/finance-for-review.md'}))
