# Реестр проектных допущений

Идентификаторы Pxx обозначают допущения, а не порядок качества. Пути источников — от корня проекта, если не сказано иначе.

## P01
- applies_to: V02;V03
- type: design_constraint
- statement: Действующие правила начисления, передачи, конвертации, несгорания личных остатков и старые права сохраняются
- value: unchanged
- unit: rules
- period_scope: entire pilot
- validation: Сверить правила и журналы с frozen baseline; не домысливать Спасибо/стаж
- implication: Нарушение исключает вариант

## P02
- applies_to: V02;V03
- type: feasibility_assumption
- statement: Доступны сверяемые ID, журналы C/R/F, остатки на общую дату, каталог, закупки и справочник прав
- value: unverified
- unit: data access
- period_scope: before launch
- validation: Владельцы HR/IT/финансы подтверждают полноту и сверку
- implication: Без критического входа budget/currency_balances uncertain

## P03
- applies_to: V02;V03
- type: project_schedule
- statement: Подготовка/тест/донаблюдение; горизонт увеличивается заранее если реальные сроки длиннее
- value: 4/8/4
- unit: weeks
- period_scope: pilot
- validation: Подтвердить достижимость до запуска; не назначать незавершённым успех
- implication: Не прогноз банковских сроков

## P04
- applies_to: V02;V03
- type: measurement_design
- statement: Практически полезные пороги эффекта и guardrails фиксируют HR/аналитик до рандомизации
- value: unset before pre-registration
- unit: metric-specific
- period_scope: future test
- validation: Нужны базы метрик, число независимых кластеров и оценка мощности
- implication: Не подбирать пороги после результата

## P05
- applies_to: V02;V03
- type: scenario_parameters
- statement: C0/R0/F0, I_C/G_R/W_R, возвраты, коррекции, цены, календарь и мощности одинаковы для вариантов при сопоставлении
- value: unknown
- unit: C/R/RUB/hours
- period_scope: shared accounting period
- validation: Финансист подставляет единый сценарий; исходники банковских параметров отсутствуют
- implication: Не заявлять реальный бюджет/эффект

## P06
- applies_to: V02;V03
- type: calculation_convention
- statement: C* и R* исключают единицы уже учтённые в базовых погашениях b_y; доли alpha/beta/gamma/delta от 0 до 1
- value: disjoint pools; [0,1]
- unit: units and fractions
- period_scope: stress scenario
- validation: Сверить по событийному календарю; прямое R и R-to-C взаимоисключающи
- implication: Иначе двойной счёт

## P07
- applies_to: V02;V03
- type: calculation_convention
- statement: k_C берётся из одинакового набора SKU/платежей; пределы 30 и 34 млн проверяются раздельно
- value: k_C unknown; B=30000000 and 34000000
- unit: RUB/C; RUB/year
- period_scope: annual stress
- validation: Полный расчёт по счетам; не использовать ориентир 1:5 как себестоимость
- implication: Сокращённая формула условна

## P08
- applies_to: V02;V03
- type: measurement_design
- statement: Возможны сопоставимые независимые группы и контроль перетока ресурса; непокупатели входят в панель признания
- value: unverified
- unit: clusters/persons
- period_scope: future test
- validation: Проверить число пулов, роли/географию, отклик, отсутствие скрытого дополнительного ресурса
- implication: Иначе процессный тест без причинного вывода

## P09
- applies_to: V02;V03
- type: unknown_requirement
- statement: Авторитетный регламент трёх сертификатов, права по ролям и условия возвратов подтверждаются до испытания
- value: unknown
- unit: rules
- period_scope: before launch
- validation: Получить правила банка; не назначать окно лимита по баннеру
- implication: Непроверенные категории не включать; обычные права сохранить

## P10
- applies_to: V02
- type: project_rule
- statement: Необязательная заявка: одна основная позиция с допустимой заменой; без резерва/бонуса/приоритета; цикл сбора и решения
- value: 7+7
- unit: calendar days
- period_scope: pre-order process
- validation: Проверить нагрузку, отклик, устаревание баланса и отсутствие давления тратить
- implication: Плановый срок ответа не обещает поставку

## P11
- applies_to: V02
- type: feasibility_assumption
- statement: Есть изменяемый незаконтрактованный закупочный микс; возможно покрыть спрос сохраняя принятые заказы и минимальный запас обычного магазина
- value: unverified
- unit: SKU quantities/RUB
- period_scope: purchase planning
- validation: Закупщик подтверждает договоры, минимальные партии и защиту обычного спроса
- implication: Без этого механизм не работает

## P12
- applies_to: V02
- type: hypothesis
- statement: Согласованные заявки предсказывают неудовлетворённый приемлемый спрос и позволяют покрыть больше потребностей при тех же деньгах
- value: effect may be zero
- unit: persons with covered need
- period_scope: pilot
- validation: Отказы/неполученный товар сохраняются; сравнить с V05
- implication: Сервисный результат не равен ценности признания

## P13
- applies_to: V02
- type: project_rule
- statement: Микс максимизирует число покрытых основных заявок; при равенстве меньший расход, затем покрытие не обслуженных групп
- value: proposed
- unit: procurement decision
- period_scope: purchase cycle
- validation: Одна потребность засчитывается один раз; проверить доступ обычных покупателей
- implication: Не утверждение о действующей закупочной политике

## P14
- applies_to: V03
- type: project_rule
- statement: Проверка ресурса после выбора до двух рабочих дней; при отсутствии ресурса снять резерв, не скрывать отказ
- value: 2
- unit: working days
- period_scope: post-choice process
- validation: Замерить нагрузку владельца; дата доставки определяется отдельно
- implication: Не обещание двухдневной доставки

## P15
- applies_to: V03
- type: feasibility_assumption
- statement: Допустим технически и регламентно атомарный резерв части личного остатка с погашением по подтверждённому исполнению
- value: unverified
- unit: transaction rule
- period_scope: before live launch
- validation: HR/IT/финансы подтверждают; old debited orders не резервировать повторно
- implication: Без защиты от двойного расхода тест на балансах не запускается

## P16
- applies_to: V03
- type: hypothesis
- statement: Есть устранимые разрывы ответственности/ресурсного согласования после выбора, а не только абсолютный дефицит
- value: effect may be zero
- unit: orders fulfilled by D*
- period_scope: pilot
- validation: Разобрать причины отказов/просрочек и нагрузку; проверить с V05
- implication: Не использовать снижение выплат через отказы как успех

## P17
- applies_to: V03
- type: project_rule
- statement: Владелец ежедневно проверяет сроки; D* и допустимая дата определяются до теста по типу награды
- value: daily; D* unset
- unit: working days/calendar horizon
- period_scope: order handling
- validation: Одинаковый D* для контроля; первоначальный таймер не сбрасывается
- implication: Ускорение не должно ухудшать чужую очередь

## P18
- applies_to: V03
- type: measurement_design
- statement: Первичная когорта: первые действительные выборы сотрудников до раскрытия режима, отказ после регистрации остаётся неуспехом
- value: fixed eligibility
- unit: first choice/person
- period_scope: future trial
- validation: Контроль состава входа, незавершённых заказов, кластеризации и перетока
- implication: Ограниченная переносимость на будущий поток

## P19
- candidate_keys: V04;V01
- type: допущение реализуемости
- parameter: Связь формы/реестра с журналами
- value: Есть разрешённый способ использовать исходный event_id; способность не подтверждена
- unit: возможность
- period: до пилота
- source: Проектирование; не факт банка
- why_needed: Не создавать второй кошелёк и дубли
- validation: IT/HR подтверждают схему доступа и тест повторной доставки
- failure_condition: Нет безопасной связи или выгрузки: запуск зависимых функций отложить

## P20
- candidate_keys: V04;V01
- type: сценарное допущение
- parameter: Сопоставимость модели
- value: Одинаковые внешние запасы цены популяция календарь; значения неизвестны
- unit: C;R;руб.;люди
- period: общая дата/год
- source: inputs/context.md; review-packet/economic-notes.md
- why_needed: Сравнивать механизм при общей основе
- validation: Финансист подставляет одинаковые исходные значения и раскрывает различающиеся события
- failure_condition: Неизвестный критический вход оставляет gate uncertain

## P21
- candidate_keys: V04
- type: проектное правило
- parameter: Содержание признания
- value: Добровольные подсказки действие/польза; ответы и публикации не новые Thanks
- unit: событие
- period: после запуска
- source: Новая процедура; review-packet/candidates/V04.md раздел 2
- why_needed: Проверить понятность и социальную ценность
- validation: Когнитивный тест и журнал одного исходного события
- failure_condition: Подавление признания или дублирование бонусов

## P22
- candidate_keys: V04
- type: неизвестный параметр
- parameter: Стоимость дополнительного времени
- value: Минуты авторов получателей руководителей HR измеряются; ставок нет
- unit: мин./событие;руб./ч
- period: пилот/год
- source: Проектная ресурсная модель; review-packet/economic-notes.md
- why_needed: Полная стоимость не равна закупкам
- validation: Замер времени и подтверждение владельцев ресурса
- failure_condition: Превышение заранее принятого лимита нагрузки

## P23
- candidate_keys: V04;V01
- type: проектный дизайн
- parameter: Окно и единица теста
- value: Полный квартал плюс месяц наблюдения; кластер руководителя/связанных команд; мощность неизвестна
- unit: квартал;месяц;кластер
- period: будущий пилот
- source: Проектирование; раздел 6 концепций
- why_needed: Покрыть квартальный цикл и исполнение
- validation: Исходные дисперсия кластеризация перетоки; расчёт мощности до рандомизации
- failure_condition: Недостаточная информативность: uncertain

## P24
- candidate_keys: V04;V01
- type: процедура задания порога
- parameter: Минимально полезный эффект и guardrails
- value: Владелец и аналитик фиксируют до рандомизации на базе исходных измерений и ресурсов; чисел нет
- unit: п.п.;мин.;руб.;слоты
- period: до пилота
- source: Проектирование; раздел 6 концепций
- why_needed: Не выбирать удобный порог после результата
- validation: Предрегистрация исходов интервалов пропусков мощности и границ ухудшения
- failure_condition: Нет зафиксированных порогов: причинный тест не готов к запуску

## P25
- candidate_keys: V04;V01
- type: допущение реализуемости
- parameter: Доступ и конфиденциальность
- value: Разрешённый канал и рабочее время по ролям; приватность и доступ не считаются одинаковыми
- unit: группа;канал;ч
- period: до/во время пилота
- source: Проектирование; раздел 5 концепций
- why_needed: Включать смены регионы непокупателей
- validation: HR проверяет роль/доступ/полномочия; работники проверяют формулировки
- failure_condition: Неохваченная группа или неприемлемое раскрытие: исправление до запуска

## P26
- candidate_keys: V04;V01
- type: проектное ограничение
- parameter: Переход и валюта
- value: Старые права 1:1; действующие ставки сохраняются; неизвестные связи событий не достраиваются
- unit: C;R;право
- period: дата перехода
- source: C01 с.10–12; новая процедура
- why_needed: Не финансировать концепцию потерей прав
- validation: Сверка C0/R0/F0 заказов резервов регламента Thanks стажа и исправлений
- failure_condition: Необъяснимое расхождение: currency_balances uncertain/fail по проверке

## P27
- candidate_keys: V01
- type: проектное правило
- parameter: Обнаружение и рассмотрение
- value: Ежемесячный разбор; добровольные сообщения и ротация приглашений; руководитель решает без квоты выдачи
- unit: разбор/месяц;приглашение
- period: квартал пилота
- source: Новая процедура; review-packet/candidates/V01.md раздел 2
- why_needed: Изменить множество замеченных вкладов
- validation: Разделить приглашённых рассмотренных признанных награждённых; аудит отказов
- failure_condition: Обязательная раздача или конкурс самопрезентации без прямого охвата

## P28
- candidate_keys: V01
- type: неизвестный параметр
- parameter: Мощность рассмотрения
- value: n_review<=60*H_available/t_case после других затрат; чисел нет
- unit: ч/месяц;мин./карточку
- period: месяц пилота
- source: Расчёт; review-packet/candidates/V01.md раздел 4
- why_needed: Учесть приглашения свободные обращения споры
- validation: Хронометраж; владелец ресурса подтверждает доступные часы
- failure_condition: Растущая очередь или превышение мощности: уменьшить масштаб

## P29
- candidate_keys: V04;V01
- type: неизвестные параметры
- parameter: Закупки и полная стоимость
- value: Цены остатки даты платежа нагрузки ставки и доступность льгот неизвестны
- unit: руб./SKU;C/SKU;R/SKU;ч;слоты
- period: год и месяцы
- source: C01 с.10/19; review-packet/economic-notes.md
- why_needed: Проверить обе границы 30 и 34 млн и мощность
- validation: Договоры склад реестр заказов ставки рабочего времени правила льгот
- failure_condition: Неподтверждённые критические значения: budget uncertain

## P30
- candidate_keys: V04;V01
- type: иллюстративное допущение
- parameter: Нормированный баланс
- value: C0=1000 R0=400 F0=600 I=150 G=500 W=300 X=100 PC=200 PR=50 T=40; без J/V; не данные ОТП
- unit: условные C/R
- period: искусственный квартал
- source: review-packet/economic-notes.md раздел Нормированная проверка
- why_needed: Только проверка арифметики сохранения
- validation: Расчёт normal/old_C/conversion/direct_R в validation.json
- failure_condition: Не использовать как прогноз или подтверждение лимита
