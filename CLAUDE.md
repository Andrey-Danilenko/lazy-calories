# Project: LazyCalories – Telegram bot for easy Food energy counting

Telegram bot for easy Food energy counting.

# Stack
- **Backend**: Python, python-telegram-bot, openai
- **Database**: PostgreSQL via SQLAlchemy 2.0 async (asyncpg driver)
- **RAG**: Qdrant (embedded, via qdrant-client) + fastembed (ONNX embeddings, multilingual)
- **Tools**: ruff (linter), uv

# Project Structure

```
lazy-calories/
├── main.py              # Composition root: build Settings + deps, wire telegram handlers, poll
├── src/
│   ├── common/                  # general-purpose, feature-agnostic infrastructure
│   │   ├── config.py            # Settings dataclass, loaded once from env (Settings.from_env)
│   │   ├── llm.py               # shared deepseek client factories (chat client + structured llm)
│   │   ├── db.py                # async SQLAlchemy engine + session factory + Base + init_models
│   │   ├── clock.py             # MOSCOW_TZ + get_moscow_time
│   │   ├── logger.py            # action/user logging (uses clock)
│   │   ├── prompts_validator.py # PromptValidator: reusable security gate over user input
│   │   └── start.py             # /start command handler
│   └── consumption/             # the food-tracking agent (records what the user ate)
│       ├── intents.py           # Intent(StrEnum): LOG_FOOD / GET_STATS / UNKNOWN
│       ├── models.py            # Product / ParsedMeal / ProductNutrition (pydantic) + Nutrition ops + scaling
│       ├── prompts.py           # classify + meal-parse + per-100g nutrition-lookup prompts
│       ├── agent.py             # ConsumptionAgent: deepseek classify + parse_meal + lookup_nutrition (LLM only)
│       ├── vector_store.py      # FoodVectorStore: Qdrant + fastembed per-100g nutrition cache
│       ├── resolver.py          # NutritionResolver: parse → vector lookup → LLM misses → scale
│       ├── storage.py           # Meal/MealProduct ORM + async MealRepository (Postgres)
│       ├── replies.py           # all user-facing Russian text + nutrition formatting
│       ├── state.py             # AgentState TypedDict (graph state only)
│       ├── graph.py             # ConsumptionGraph: thin LangGraph nodes + routing + run()
│       └── bot.py               # make_message_handler(graph): telegram glue for food messages
└── stored_data/         # embedded Qdrant vector store (gitignored); meals live in Postgres
```

## Apps Overview

### consumption — food КБЖУ agent
A LangGraph agent (`src/consumption/graph.py`) drives two use cases from free-text
Russian messages:
1. **Log food** — the user describes what they ate (any units: grams, ml, pieces,
   portions, or an approximate description). deepseek *parses* the meal into named products
   with an estimated eaten mass; КБЖУ come from the Qdrant vector cache (per 100 g) when a
   product is known, and only otherwise from the LLM (`RAG`, see Key Patterns). Each
   per-product record (scaled to the eaten mass) is appended to today's file, and the user
   is shown the summed КБЖУ for the whole meal.
2. **Daily stats** — the user asks how much they ate today → sum every product of every
   meal → reply.

Graph: `validate` (security gate) → `orchestrator` (intent classifier) → conditional →
`extract`/`get_stats`/`fallback`. The `extract` node delegates to `NutritionResolver`
(parse → vector lookup → LLM misses → scale); the log-food path is `extract` → conditional →
`save_meal` | retry `extract` (up to `MAX_EXTRACTION_ATTEMPTS`) | `extract_failed`. A
rejected message goes `validate` → `rejected`. `src/consumption/bot.make_message_handler`
binds a `ConsumptionGraph` to the telegram handler, which calls `graph.run` and sends the
reply.

## Architecture & Layering
- **`common` is feature-agnostic**: config, the shared LLM factory, clock, logging, and the
  reusable `PromptValidator`. It must NOT import from `consumption` (dependency points one
  way: `consumption` → `common`).
- **`consumption` owns the agent**: NLU (`agent.py`), persistence (`storage.py`),
  orchestration (`graph.py`), presentation (`replies.py`), and telegram glue (`bot.py`).
- **Agent vs graph split**: `ConsumptionAgent` holds *every* LLM call and nothing else.
  `ConsumptionGraph` nodes are thin — they move state and delegate to the agent
  (intelligence), `NutritionResolver` (parse+lookup+cache+scale), `FoodVectorStore` (vector
  search/cache), `MealRepository` (persistence) and `replies` (text). No business detail
  lives in a node. `NutritionResolver` is the application service that combines the agent
  (LLM) with `FoodVectorStore` — this is where the RAG flow lives, keeping the agent LLM-only.
- **Composition root**: `main.build_application` builds the async DB engine + session factory
  (`common/db`), wires them through `make_message_handler(session_factory)` into the graph, and
  registers `post_init`/`post_shutdown` hooks that call `init_models` (create tables) on startup
  and `engine.dispose()` on shutdown. The agent, resolver, repository, validator and graph are
  constructed and injected via constructors.

## Key Patterns
- **LLM**: deepseek (OpenAI-compatible). One config source (`common/config.Settings`) and one
  client factory (`common/llm`): `create_chat_client` (raw `AsyncOpenAI`, `json_object`) for
  intent classification + prompt validation, `create_structured_llm` for meal parsing
  (`ParsedMeal`) and per-100g nutrition lookup (`ProductNutritionList`) via
  `ChatOpenAI(...).with_structured_output(...)`, so malformed output is caught and retried by
  the `extract` node.
- **RAG (nutrition cache)**: `FoodVectorStore` (`consumption/vector_store.py`) is a Qdrant
  collection of **per-100g** product КБЖУ, embedded with fastembed (multilingual model, for
  Russian names). `NutritionResolver` parses a meal into `{name, grams}` items, looks each
  name up in the store (cosine ≥ `NUTRITION_SCORE_THRESHOLD`), asks the LLM for **misses only**
  (one batched `lookup_nutrition` call), writes the new references back (deterministic uuid5
  id per name → dedup), then scales every reference to the eaten mass (`models.scale_to_eaten`).
  Best case = 1 LLM call (parse only); the cache warms so cost + КБЖУ variance drop over time.
  Deployment: embedded persistent at `QDRANT_PATH` (default `stored_data/qdrant`) unless
  `QDRANT_URL` points at a Qdrant server. Blocking Qdrant/fastembed calls run in `to_thread`.
- **Safety**: every user message is validated first by `PromptValidator`
  (`src/common/prompts_validator.py`) via a deepseek call returning a `ValidatorResults`
  pydantic model. The `validate` graph node gates the flow; on rejection (or any
  validation error — it fails closed) the user gets a generic refusal and nothing is
  classified or stored.
- **Storage**: PostgreSQL via async SQLAlchemy. `common/db.py` builds the async engine +
  `async_sessionmaker` from `settings.database_url` (`postgresql+asyncpg://…`); tables are
  created at startup by `init_models` (`Base.metadata.create_all`, no Alembic — schema is
  managed in code). `MealRepository` (`consumption/storage.py`) owns two ORM tables, `meals`
  and `meal_products` (one row per product, FK + cascade). `append_meal` inserts a meal with
  its products; `read_today_totals` is a SQL `SUM` over `meal_products` joined to today's
  meals for the user. The injectable `clock` (default `get_moscow_time`) defines the day
  boundary and keeps it testable. All repo methods are `async` and awaited from the graph.
- **Tracing**: LangSmith. The deepseek client is wrapped with `wrap_openai` and the entry
  points (`ConsumptionGraph.run`, `classify_intent`, `parse_meal`, `lookup_nutrition`,
  `validate_prompt`) are `@traceable`, so each message is one trace tree (graph → nodes → LLM
  calls). Enabled via
  env: `LANGSMITH_TRACING=true`, `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT` (see `.env-template`).

# Development Rules
- **Linter**: ruff
- **Comments**: Only when logic needs explanation, not for self-explanatory code
- **Utilities**: Reusable, feature-agnostic helpers → `lazy-calories/src/common/` (e.g. `clock.py`, `llm.py`)
- **Code style**: DRY, Clean Code, SOLID. Split long functions. No single-use variables.
- **Imports**: Avoid nested imports unless necessary
- **CLAUDE.md maintenance**: When adding/modifying apps or models, update the "Project Structure" and "Apps Overview" sections in this file to keep context accurate


## Design System
- **Language**:
  - Users use Russian, so all text sending to the user should be in Russian
  - Developers use English, so all text that is programmatically generated should be in english (Classes, variables, comments, API responses, error messages, etc.)
