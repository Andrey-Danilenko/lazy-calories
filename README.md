# LazyColories

Telegram-бот для ленивого подсчёта КБЖУ (калории, белки, жиры, углеводы). Пользователь пишет свободным текстом, что он съел, а LLM-агент разбирает приём пищи на отдельные продукты, считает их КБЖУ и сохраняет запись за день.

## Возможности

- **Логирование еды** — опишите приём пищи в любых единицах (граммы, мл, штуки, порции или приблизительно). Агент разбивает его на отдельные продукты с КБЖУ, сохраняет и показывает суммарные значения за весь приём.
- **Дневная статистика** — спросите, сколько вы съели сегодня, и бот просуммирует КБЖУ по всем приёмам пищи за день.
- **Защита ввода** — каждое сообщение проходит через security-гейт (`PromptValidator`) до классификации и сохранения; при отказе или ошибке валидации (fail-closed) пользователь получает общий отказ.

> Пользовательский интерфейс — на русском. Код, имена, комментарии и логи — на английском.

## Стек

- **Язык**: Python 3.14+
- **Telegram**: [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- **LLM**: deepseek (OpenAI-совместимый API) через `openai` и `langchain-openai`
- **Оркестрация**: [LangGraph](https://github.com/langchain-ai/langgraph)
- **Валидация моделей**: pydantic
- **Трейсинг**: LangSmith
- **Инструменты**: [uv](https://github.com/astral-sh/uv) (зависимости), ruff (линтер/форматтер)

## Архитектура

Сообщение пользователя проходит по графу LangGraph:

```
validate (security) → orchestrator (классификация интента) → ветвление:
  ├─ extract → save_meal | retry extract (до MAX_EXTRACTION_ATTEMPTS) | extract_failed
  ├─ get_stats
  └─ fallback
отклонённое сообщение: validate → rejected
```

Слои разделены, зависимости направлены в одну сторону (`consumption` → `common`):

- **`src/common/`** — feature-agnostic инфраструктура: конфиг (`config.py`), фабрика LLM-клиентов (`llm.py`), часы/таймзона (`clock.py`), логирование (`logger.py`), переиспользуемый `PromptValidator` (`prompts_validator.py`), обработчик `/start` (`start.py`).
- **`src/consumption/`** — агент учёта еды: NLU (`agent.py`), хранилище (`storage.py`), граф (`graph.py`), тексты ответов (`replies.py`), Telegram-связка (`bot.py`).

**Разделение agent/graph**: `ConsumptionAgent` держит все вызовы LLM и ничего больше; узлы `ConsumptionGraph` тонкие — они двигают состояние и делегируют агенту (интеллект), `MealRepository` (хранение) и `replies` (тексты).

Подробнее — в [CLAUDE.md](CLAUDE.md).

## Хранение

Без БД. `MealRepository` пишет по одному JSONL-файлу на пользователя в день:

```
stored_data/{user_id}/{YYYY-MM-DD}.jsonl
```

Одна строка — один приём пищи со списком `products` (`{name, weight_grams, energy, protein, fat, carbohydrates}`).

## Установка

Требуется Python 3.14+ и [uv](https://github.com/astral-sh/uv).

```bash
uv sync
```

## Настройка

Скопируйте шаблон окружения и заполните значения:

```bash
cp .env-template .env
```

| Переменная | Описание |
|---|---|
| `DEEPSEEK_API_KEY` | Ключ API deepseek |
| `TELEGRAM_BOT_TOKEN` | Токен Telegram-бота (от @BotFather) |
| `LANGSMITH_TRACING` | `true` для включения трейсинга LangSmith |
| `LANGSMITH_API_KEY` | Ключ API LangSmith |
| `LANGSMITH_PROJECT` | Имя проекта в LangSmith |
| `LANGSMITH_ENDPOINT` | Эндпоинт LangSmith |

## Запуск

```bash
uv run python main.py
```

Бот стартует в режиме polling. Откройте чат с ботом в Telegram, отправьте `/start` и напишите, что вы съели.

## Разработка

Линтинг и форматирование через ruff:

```bash
uv run ruff check .
uv run ruff format .
```

Правила стиля: DRY, Clean Code, SOLID; комментарии — только там, где логика требует пояснения; переиспользуемые хелперы — в `src/common/`. См. раздел Development Rules в [CLAUDE.md](CLAUDE.md).
