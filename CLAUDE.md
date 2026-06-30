# Project: LazyColories – Telegram bot for easy Food energy counting

Telegram bot for easy Food energy counting.

# Stack
- **Backend**: Python, python-telegram-bot, openai
- **Tools**: ruff (linter), uv

# Project Structure

```
lazyColories/
├── main.py              # Composition root: build Settings + deps, wire telegram handlers, poll
├── src/
│   ├── common/                  # general-purpose, feature-agnostic infrastructure
│   │   ├── config.py            # Settings dataclass, loaded once from env (Settings.from_env)
│   │   ├── llm.py               # shared deepseek client factories (chat client + structured llm)
│   │   ├── clock.py             # MOSCOW_TZ + get_moscow_time
│   │   ├── logger.py            # action/user logging (uses clock)
│   │   ├── prompts_validator.py # PromptValidator: reusable security gate over user input
│   │   └── start.py             # /start command handler
│   └── consumption/             # the food-tracking agent (records what the user ate)
│       ├── intents.py           # Intent(StrEnum): LOG_FOOD / GET_STATS / UNKNOWN
│       ├── models.py            # Product/Meal (pydantic) + Nutrition (TypedDict) & nutrition ops
│       ├── prompts.py           # classify + meal-extraction prompts
│       ├── agent.py             # ConsumptionAgent: deepseek classify + structured meal extract (LLM only)
│       ├── storage.py           # MealRepository: JSONL meal storage under stored_data/
│       ├── replies.py           # all user-facing Russian text + nutrition formatting
│       ├── state.py             # AgentState TypedDict (graph state only)
│       ├── graph.py             # ConsumptionGraph: thin LangGraph nodes + routing + run()
│       └── bot.py               # make_message_handler(graph): telegram glue for food messages
└── stored_data/         # per-user, per-day meal records (gitignored)
```

## Apps Overview

### consumption — food КБЖУ agent
A LangGraph agent (`src/consumption/graph.py`) drives two use cases from free-text
Russian messages:
1. **Log food** — the user describes what they ate (any units: grams, ml, pieces,
   portions, or an approximate description). deepseek breaks the meal into individual
   products, each with a name + КБЖУ; the per-product list is appended to today's file,
   and the user is shown the summed КБЖУ for the whole meal.
2. **Daily stats** — the user asks how much they ate today → sum every product of every
   meal → reply.

Graph: `validate` (security gate) → `orchestrator` (intent classifier) → conditional →
`extract`/`get_stats`/`fallback`. The log-food path is `extract` → conditional →
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
  (intelligence), `MealRepository` (persistence) and `replies` (text). No business detail
  lives in a node.
- **Composition root**: `main.build_application(settings)` constructs the agent, repository,
  validator and graph and injects them (constructor injection). No module builds
  import-time singletons; dependencies are passed in (defaults come from `common/llm`).

## Key Patterns
- **LLM**: deepseek (OpenAI-compatible). One config source (`common/config.Settings`) and one
  client factory (`common/llm`): `create_chat_client` (raw `AsyncOpenAI`, `json_object`) for
  intent classification + prompt validation, `create_structured_llm` for meal extraction via
  `ChatOpenAI(...).with_structured_output(Meal)` (pydantic `Meal`/`Product` in
  `consumption/models.py`) so malformed output is caught and retried by the `extract` node.
- **Safety**: every user message is validated first by `PromptValidator`
  (`src/common/prompts_validator.py`) via a deepseek call returning a `ValidatorResults`
  pydantic model. The `validate` graph node gates the flow; on rejection (or any
  validation error — it fails closed) the user gets a generic refusal and nothing is
  classified or stored.
- **Storage**: no DB. `MealRepository` (`consumption/storage.py`) writes one JSONL file per
  user per day at `stored_data/{user_id}/{YYYY-MM-DD}.jsonl`; one meal record per line, each
  holding a `products` list (`{name, weight_grams, energy, protein, fat, carbohydrates}`).
  `read_today_totals` reads across products (and the legacy single-`nutrition` format) and
  reuses `models.sum_nutrition`. The injectable `clock` (default `get_moscow_time`) makes it
  testable.
- **Tracing**: LangSmith. The deepseek client is wrapped with `wrap_openai` and the entry
  points (`ConsumptionGraph.run`, `classify_intent`, `extract_meal`, `validate_prompt`) are
  `@traceable`, so each message is one trace tree (graph → nodes → LLM calls). Enabled via
  env: `LANGSMITH_TRACING=true`, `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT` (see `.env-template`).

# Development Rules
- **Linter**: ruff
- **Comments**: Only when logic needs explanation, not for self-explanatory code
- **Utilities**: Reusable, feature-agnostic helpers → `lazyColories/src/common/` (e.g. `clock.py`, `llm.py`)
- **Code style**: DRY, Clean Code, SOLID. Split long functions. No single-use variables.
- **Imports**: Avoid nested imports unless necessary
- **CLAUDE.md maintenance**: When adding/modifying apps or models, update the "Project Structure" and "Apps Overview" sections in this file to keep context accurate


## Design System
- **Language**:
  - Users use Russian, so all text sending to the user should be in Russian
  - Developers use English, so all text that is programmatically generated should be in english (Classes, variables, comments, API responses, error messages, etc.)
