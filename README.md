# ОТП Мания — рабочая папка кейса

Здесь готовим решение кейса ОТП Банка для Changellenge Cup Moscow 2026: исследуем проблему признания сотрудников, анализируем отзывы, сравниваем концепции и проверяем экономику при фиксированном бюджете.

**Сейчас:** подготовлены [wiki](knowledge/wiki/INDEX.md), [диагностика и входной пакет](analysis/preparation/README.md); завершён [сквозной пилот pilot-001](analysis/iterations/pilot-001/pilot-report.md). Созданы четыре концепции, сопоставимые финансовые/evidence проверки и независимое ревью с baseline. Допустимый победитель не выбран: реальные бюджет и валютные балансы остаются неподтверждёнными.

Одна разрешённая итерация запечатана в [rounds/001](analysis/iterations/pilot-001/rounds/001/snapshot.json), хеши проверены. Запуск завершён по iteration_limit; общая конфигурация до трёх итераций сохранена. Следующие циклы и презентация не запускались. [Первоначальный needs_inputs](analysis/iterations/pilot-001/report.md) сохранён как история.

| Папка / файл | Назначение |
|---|---|
| [AGENTS.md](AGENTS.md) | Общие инструкции Codex |
| [project/brief.md](project/brief.md) | Задача, ограничения, требования к сдаче |
| [project/status.md](project/status.md) | Что сделано и откуда продолжать |
| [project/decisions.md](project/decisions.md) | Зафиксированные решения о процессе и будущем решении кейса |
| [knowledge/](knowledge/README.md) | Исходники raw и структурированная wiki |
| [research/](research/README.md) | Проверка источников, утверждения, точечный ресерч |
| [analysis/](analysis/README.md) | Диагностика, варианты, метрики и расчёты |
| [analysis/iterations/](analysis/iterations/README.md) | Запуски, снимки и сравнение итераций |
| [deliverables/](deliverables/README.md) | Будущая презентация, модель и приложения |
| [templates/](templates/README.md) | Шаблоны задания, источника, анализа и проверки |
| [docs/agent-setup/](docs/agent-setup/README.md) | Архитектура, роли, workflow и проверки системы |
| [.agents/skills/](.agents/skills/README.md) | Восемь проектных skills; knowledge-curation и case-iteration вызываются явно |
| [.codex/](.codex/README.md) | Шесть custom agents и предел двух дочерних исполнителей |

Для продолжения начните с текущего статуса и итогового отчёта пилота. Реестры wiki описывают подготовку знаний; подтверждённый эффект для банка не установлен. Модели, provider, разрешения среды и подключения наследуются; глобальные настройки не изменяются. Установка системы сама по себе не является запуском.
