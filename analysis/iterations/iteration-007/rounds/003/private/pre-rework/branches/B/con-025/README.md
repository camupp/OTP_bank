# CON-025@v1: помесячное обеспечение

Родитель CON-023@v2. Изменён только заранее подписываемый календарь20-часовых бронирований по полному родительскому прогнозу всех обещаний7200/E24. Все роли/минуты/нормы/квалификация/QA/setup/награды/сроки/права прежние. Фактические normal/top/U или покупки исходных120участников не участвуют в финансовом спросе.

Основные материалы: [concept.md](concept.md), [cards.md](cards.md), [employee-card.md](employee-card.md), [source-to-award.md](source-to-award.md), [completion-report.md](completion-report.md). Данные: [booking-delta.csv](booking-delta.csv), [resource-supply.csv](resource-supply.csv), [resource-savings.csv](resource-savings.csv), [self-check.json](self-check.json), [parent-reuse.json](parent-reuse.json), [provenance.json](provenance.json), [artifacts.sha256.json](artifacts.sha256.json).

В закрытом родителе ничего не исполняется/не изменяется. Его38результатов переиспользованы поSHA:3524личных/2600ролевыхстрок,304trace,432календарныхстроки, личные суммы и денежный core. AST всех scoring/C3функций и recognition-spec совпадают семантически. В текущих decisions изменены только candidate_key/decision_version/rule hash подписываемого пакета; подписанные parent-акты не авторизуют текущую версию. Это изменение метаданных не меняет право/сумму/ранг. Новые QA-пробы рассчитаны прямо, без повторного38scoring. Общие source не меняются.

Python3.14.8, стандартная библиотека, `-B`/dont_write_bytecode. До freeze из корня проекта исполнены только текущие скрипты:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B analysis/iterations/iteration-007/rounds/003/branches/B/con-025/build_resources.py
PYTHONDONTWRITEBYTECODE=1 python3 -B analysis/iterations/iteration-007/rounds/003/branches/B/con-025/adapt_metadata.py
PYTHONDONTWRITEBYTECODE=1 python3 -B analysis/iterations/iteration-007/rounds/003/branches/B/con-025/self_check.py
```

Для воспроизведения после freeze нужна рабочая копия с той же относительной структурой, без изменения закрытых снимков. evaluator.py остаётся исполнимым калькулятором primitive source; его full38 export здесь повторно не выполнялся. make_money_examples.py не выполнялся, таблица личных примеров унаследована с нулевой семантической дельтой. Никакие старые build/export/selfcheck не запускались.

Каждый11232ключ новой monthly-resource и booking-delta соответствует parent scope:39месяцев×4роли×3shop×2fixed×3QA×2labor×2substitution. Annual-resource/savings содержат те же288ролевыхсрезов×5периодов (годы1/2/3,хвост37–39,все39). Источник прогнозного спроса — полный parent monthly-resource по pinnedSHA, не observed выплаты. Использованный резерв входит в actual-work, а простой оплачивается отдельно без повторной оплаты usedчасов. Setup сохранён отдельно. Касса/стоимость fail-срезов — требования условного сценария, не исполненные банковские платежи.

Supply перечисляет конечные позицииA/B и занятости, готовность/квалификацию/отводы; это требования к заранее подписанному договору, не реальные сотрудники. Будущие занятости закреплены до обещаний; в unbookedмесяце нет неоплаченного дежурства или требования доступности. Любые дополнительные реальные standby/минимальные платежи/затраты на переграфики требуют отдельного обеспечения и могут уничтожить экономию; они не объявляются известным нулём. Employee-блоки — защищённое оплачиваемое время фактических заявителей, не четыре заместителя.

Месячная арифметика сохраняет30условныхпрофилей/42fail; фактическая мощность, финансирование, intra-month rehearsal, SKU/ledger/эффект остаются неизвестными. Положительные C3 U600/420 в self-check — явно созданные in-memory примеры, не действия/проводки банка. В38общих источниках U0. Повторные U-снимки не складывают в новые выдачи. Независимые checks/review и выбор — вне этой ветки. branch.json complete пишется последним; после freeze ветка не меняется.
