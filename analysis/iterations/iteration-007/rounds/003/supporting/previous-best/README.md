# CON-023@v2: состав и воспроизведение

Результат продолжает существующую ветку B второго раунда. CON-023@v2 — единственная целевая доработка CON-023@v1 по пяти C3-дефектам, без изменения наград или ресурса. Основной документ — [concept.md](concept.md); три ролевые карточки — [cards.md](cards.md), личная ценность — [employee-card.md](employee-card.md). Итог и границы проверок — [completion-report.md](completion-report.md). Это аналитическая концепция на синтетических данных, без реальных API и выплат.

Версия проверена на Python **3.14.8**, только стандартная библиотека. Рабочий корень `/Users/davatoros/Desktop/OTP_bank`; старый абсолютный путь не нужен. Из корня проекта до freeze исполнены:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B analysis/iterations/iteration-007/rounds/002/branches/B/con-023/evaluator.py
PYTHONDONTWRITEBYTECODE=1 python3 -B analysis/iterations/iteration-007/rounds/002/branches/B/con-023/build_resources.py
PYTHONDONTWRITEBYTECODE=1 python3 -B analysis/iterations/iteration-007/rounds/002/branches/B/con-023/make_money_examples.py
PYTHONDONTWRITEBYTECODE=1 python3 -B analysis/iterations/iteration-007/rounds/002/branches/B/con-023/self_check.py
```

Скрипты пишут только рядом с собой. Для повторного запуска после freeze нужна разрешённая рабочая копия с сохранённой относительной структурой; закрытую ветку не перезаписывать. Ни один скрипт не исполняет старые экспорты или денежную модель. `build_resources.py` читает два прежних CSV как данные: `iteration-007/incumbent/first-launch.csv` и `rounds/001/branches/B/con-021/common-shop-inputs.csv`. Public reader читает только назначенные source/patches. `sys.dont_write_bytecode=True` установлен до динамического импорта, чтобы не создавать cache во входах.

| Файл | Содержание |
|---|---|
| [metrics-spec.json](metrics-spec.json), [source-to-award.md](source-to-award.md) | Правила normal/strong/ранга, grain, независимость, путь от источника к валюте |
| [decisions.csv](decisions.csv), [unit-decisions.csv](unit-decisions.csv) | 3524 личных и 2600 ролевых квартальных строк по 38 снимкам |
| [traces.json](traces.json), [calendar-traces.csv](calendar-traces.csv) | 304 компактных различающихся исхода и 432 временных проверки R4; refs восстанавливаются через публичный reader |
| [group-top-reserve.csv](group-top-reserve.csv), [window-guarantee.csv](window-guarantee.csv) | Пул top отдельно от повторяемых личных максимумов; два квартала своего фиксированного окна |
| [finance-spec.json](finance-spec.json), [assumptions.csv](assumptions.csv) | Неизменные денежные ставки/хеши и отдельно новые проектные допущения |
| [money-examples.csv](money-examples.csv) | 12 личных путей до условного SKU2500C/500руб., ожидание и удержание |
| [resource-stages.csv](resource-stages.csv), [monthly-resource.csv](monthly-resource.csv) | Стадии/счётчики/минуты и 11232 строки всех ролей m1–39 |
| [annual-resource.csv](annual-resource.csv), [setup-resource.csv](setup-resource.csv) | 1440 свернутых строк годов/хвоста/всего39 и отдельный setup m−2…0 |
| [self-check.json](self-check.json), [self_check.py](self_check.py) |123 авторских проверки: прежние112 и11узких проверок C3v2/неизменности ресурса;72ресурсных сочетания и ограничения C1–C7 |
| [c3-rework-examples.json](c3-rework-examples.json) | Два положительных performed-act примера, пять отрицательных, физическая целостность audit и replay; только in-memory данные |
| [rework-baseline.json](rework-baseline.json) | SHA собственных файлов до доработки и semanticSHA четырёх ресурсныхCSV без поля candidate |
| [provenance.json](provenance.json), [artifacts.sha256.json](artifacts.sha256.json) | Проверенные SHA назначенных входов и окончательных файлов своей концепции |

`earned` в unit-таблице означает расчётное выполнение normal, а не выплату. `calculated_state`, `source_review_errors`, `authorization_errors`, earned-held, conditional и U различаются. Новые общие панели содержат source-review, но не фактическую авторизацию награды: **U=0**. Дефект подписи удерживает движение, а не известное расчётное право/ранг. В отдельных, явно обозначенных in-memory positive-примерах добавлены правильно выполненные source/batch/award акты с точным пакетом; это не обновление исходников или подтверждение банковского действия. При date-only quality-close ранние внутридневные source-акты удерживаются до нового подтверждения после конца дня. Не суммировать повторённые личные `top_conditional_R`; один групповой резерв находится в group-top-reserve.csv. Финансовый benchmark7200 и его календарь не заменяются120 участниками R1 или девятью представителями R4.

В monthly-resource.csv `unique_additional_people` — номинальное число20-часовых ресурсных позиций, не подтверждённый персональный roster. Для employee это агрегат освобождаемого оплаченного времени реальных заявителей, не число людей, которые могут подать чужие заявления. `capacity_conditional_ready` подтверждает только месячную арифметику. `earliest_finish_month` — нижняя календарная оценка FIFO при доступной будущей мощности для уже накопленной очереди; не обещание фактической даты/исполнения внутри месяца. Полной кадровой/временной обеспеченности эти столбцы не доказывают.

Freeze фиксируется записью branch.json со статусом complete после всех остальных файлов. Содержательные правки после этого требуют порученной следующей версии; независимые проверяющие сохраняют свои результаты вне этой ветки.
