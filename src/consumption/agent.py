import json

from langsmith import traceable

from src.common.config import settings
from src.common.llm import create_chat_client
from src.common.llm import create_structured_llm
from src.consumption.intents import Intent
from src.consumption.models import Meal
from src.consumption.prompts import CLASSIFY_PROMPT
from src.consumption.prompts import NUTRITION_PROMPT


class ConsumptionAgent:
    def __init__(self):
        self._model = settings.deepseek_model
        self._chat_client = create_chat_client()
        self._meal_extractor = create_structured_llm(Meal)

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

    @traceable(name="extract_meal")
    async def extract_meal(self, message: str) -> Meal:
        return await self._meal_extractor.ainvoke([("system", NUTRITION_PROMPT), ("human", message)])
