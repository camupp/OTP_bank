# Общая диагностика перед пилотом

Подготовлено по поручению 27.10.2026; концепции не разрабатывались. Основной результат — [diagnosis.md](diagnosis.md), компактная передача — [summary_for_inputs.md](summary_for_inputs.md).

| Артефакт | Назначение |
|---|---|
| [Методология и кодбук](methodology.md) | Единица наблюдения, преобразования, схемы кодов и ограничения |
| [responses.csv](responses.csv) | Все 1 913 строк с исходным номером, оценками, текстом и кодами; имя не копировалось |
| [audit.json](audit.json), [data_issues.csv](data_issues.csv) | Структура, пропуски, маркеры и точные строки проблем |
| [rating_distributions.csv](rating_distributions.csv), [rating_summary.csv](rating_summary.csv) | Распределения, знаменатели и чувствительность |
| [exact_duplicate_groups.csv](exact_duplicate_groups.csv) | Совпадения A:T, не список повторных сотрудников |
| [monthly_descriptive.csv](monthly_descriptive.csv) | Объём ответов и описательные средние по месяцам; не причинный тренд |
| [theme_counts.csv](theme_counts.csv) | Мультикодовые частоты с двумя знаменателями и локаторами |
| [manual_decisions.tsv](manual_decisions.tsv), [manual_review.csv](manual_review.csv) | Содержательные решения агента и их применение к точным повторениям текста |
| [review_sample_selection.json](review_sample_selection.json) | Seed и строки стратифицированной части проверки |
| [quotes.csv](quotes.csv) | Полные точные тексты выбранных ячеек для перепроверки |
| [source_manifest.json](source_manifest.json), [validation.json](validation.json) | Версия исходника и результаты проверок |
| [analyze_feedback.py](analyze_feedback.py), [write_reports.py](write_reports.py) | Воспроизводимый расчёт и сборка отчёта |

Для повторения из корня проекта запустить `analyze_feedback.py`, затем `write_reports.py` bundled Python, указанным в методологии. `manual_decisions.tsv` — зафиксированный аналитический вход, а не автоматически воспроизводимая независимая экспертиза. Raw не изменяется.
