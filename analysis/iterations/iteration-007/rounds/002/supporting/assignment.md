# Задание разработчикам второго раунда

База путей — analysis/iterations/iteration-007/rounds/002. Общие входы: inputs/{context,evidence,diagnosis,baseline}.md и rubric.json; plan.json (своё задание), supporting/round002-common-assumptions.md, resource-menu.json, common-checks.md, measurement-contract.md, reward-basis.md, employee-profiles.md и finance-basis/. Исторический контроль ../../incumbent/ сохраняется неизменным, нового выбранного чемпиона нет.

## Источники

Старый supporting/fixtures: source/, patches/, README, dictionary, assumptions, manifest. Новый supporting/round002-stress: публичные файлы по manifest, включая reader.py, business-config.json, source/, patches/, dictionary/assumptions/README. Manifest нового пакета 206b8c7cc0e84021c01b3d2f544a07ac909536e5f7498766809eee127532210c; старого 2a8d8effe027296dd4a0b52a2717b2c8ac2dc75303af3f1bf56f8f8540ad3edc. Reader.expand_scenario(name, old_fixture_root, variant=None), scenario_index(old_fixture_root), business_configs(group,period,work_type=None,version=1). 23legacy+15новых=38снимков. Legacy не изменён, business-config — отдельное новое проспективное допущение.

Не читать oracle/, generator/validation старого источника, новый coordinator-only/, private/ и текущую другую ветку. Публичный reader не содержит scoring; его можно использовать. Включить sys.dont_write_bytecode=True или PYTHONDONTWRITEBYTECODE=1 до импорта, чтобы не писать в источники/закрытые снимки. Никогда не запускать экспорты моделей закрытых раундов. Своего завершённого родителя можно скопировать в свою новую ветку и адаптировать; закрытую копию только читать.

Панели120человек и9представителей не заменяют финансовый benchmark7200 с прежними38/22/4.5 исходными QA-инспекциями; сравнение ресурса на одной основе. Все данные/цели/слотыресурса — сценарные предположения, не стек/штат/факты банка. Не использовать готовое значение, имя панели или person_id вместо собственного алгоритма изполей. Не предполагать только P1/P2: читать настоящие period/window/date, R4 проверяет персональные окна с15-го. Новые source review, подпись бизнес-акта и действительная авторизация/проводка — разные действия; отсутствующие не объявлять выполненными. Право/условный максимум не исчезают.

## Выходы

A — CON-022@v1, parent020@v2, только branches/A/{branch.json,con-022/}. B — CON-023@v1, parents018@v2+021@v2, только branches/B/{branch.json,con-023/}. Одна целостная версия каждой по8разделам skill-контракта, три понятные карточки, metrics-spec.json, source-to-award.md, employee-card.md, evaluator.py (аналитический калькулятор), decisions.csv/traces.json/money-examples.csv, finance-spec.json, assumptions.csv, resource-stages.csv и monthly-resource.csv. Полные события не дублировать в traces: точные устойчивые ссылки и компактные примеры каждого различающего правила.

Отдельно показать source-поля/владельца/единицы/достаточность/normal/сильныйуровень/порядок/ничьи/неполноту и конечные суммы. Полный оплаченный ресурс по ролям и месяцам с setup/хвостом/простоем/пиком/годовой суммой; 220база отдельно от резерва. Не удваивать использованный резерв в цене работ. Изменённые операции обосновать, не просто урезать минуты. Прежние денежные ставки/окна/гарантии/остатки сохраняются. Авторский self-check не независимый допуск. Branch.json complete записать последним и сообщить freeze.
