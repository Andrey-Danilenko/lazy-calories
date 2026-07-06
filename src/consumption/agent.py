import json

from langsmith import traceable

from src.common.config import settings
from src.common.llm import create_chat_client
from src.common.llm import create_structured_llm
from src.consumption.intents import Intent
from src.consumption.models import ParsedMeal
from src.consumption.models import ProductNutritionList
from src.consumption.prompts import CLASSIFY_PROMPT
from src.consumption.prompts import NUTRITION_LOOKUP_PROMPT
from src.consumption.prompts import PARSE_PROMPT


class ConsumptionAgent:
    def __init__(self):
        self._model = settings.deepseek_model
        self._chat_client = create_chat_client()
        self._meal_parser = create_structured_llm(ParsedMeal)
        self._nutrition_lookup = create_structured_llm(ProductNutritionList)

    async def _ask_json(self, system_prompt: str, user_message: str) -> dict:
        response = await self._chat_client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content or "")

    @traceable(name="classify_intent")
    async def classify_intent(self, message: str) -> Intent:
        result = await self._ask_json(CLASSIFY_PROMPT, message)
        intent = result.get("intent")
        if intent in (Intent.LOG_FOOD, Intent.GET_STATS):
            return Intent(intent)
        return Intent.UNKNOWN

    @traceable(name="parse_meal")
    async def parse_meal(self, message: str) -> ParsedMeal:
        return await self._meal_parser.ainvoke([("system", PARSE_PROMPT), ("human", message)])

    @traceable(name="lookup_nutrition")
    async def lookup_nutrition(self, names: list[str]) -> ProductNutritionList:
        user_message = "\n".join(names)
        return await self._nutrition_lookup.ainvoke([("system", NUTRITION_LOOKUP_PROMPT), ("human", user_message)])
