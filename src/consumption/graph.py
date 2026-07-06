import logging

from langgraph.graph import END
from langgraph.graph import START
from langgraph.graph import StateGraph
from langsmith import traceable

from src.common.prompts_validator import PromptValidator
from src.consumption import replies
from src.consumption.agent import ConsumptionAgent
from src.consumption.intents import Intent
from src.consumption.models import is_empty_nutrition
from src.consumption.models import sum_nutrition
from src.consumption.resolver import NutritionResolver
from src.consumption.state import AgentState
from src.consumption.storage import MealRepository

logger = logging.getLogger(__name__)

MAX_EXTRACTION_ATTEMPTS = 2


class ConsumptionGraph:
    def __init__(
        self,
        agent: ConsumptionAgent,
        resolver: NutritionResolver,
        repository: MealRepository,
        validator: PromptValidator,
        max_extraction_attempts: int = MAX_EXTRACTION_ATTEMPTS,
    ):
        self._agent = agent
        self._resolver = resolver
        self._repository = repository
        self._validator = validator
        self._max_attempts = max_extraction_attempts
        self._compiled = self._build()

    async def _validate_node(self, state: AgentState) -> AgentState:
        result = await self._validator.validate(state["message"])
        state["approved"] = result.approved
        return state

    async def _orchestrator_node(self, state: AgentState) -> AgentState:
        state["intent"] = await self._agent.classify_intent(state["message"])
        return state

    async def _extract_node(self, state: AgentState) -> AgentState:
        state["attempts"] += 1
        try:
            state["products"] = await self._resolver.resolve(state["message"]) or None
        except Exception as error:
            logger.warning("Meal extraction failed (attempt %s): %s", state["attempts"], error)
            state["products"] = None
        return state

    async def _save_meal_node(self, state: AgentState) -> AgentState:
        await self._repository.append_meal(state["user_id"], state["message"], state["products"])
        total = sum_nutrition(state["products"])
        state["reply"] = replies.meal_logged(total)
        return state

    async def _extract_failed_node(self, state: AgentState) -> AgentState:
        state["reply"] = replies.EXTRACTION_FAILED_REPLY
        return state

    async def _get_stats_node(self, state: AgentState) -> AgentState:
        totals = await self._repository.read_today_totals(state["user_id"])
        state["reply"] = replies.NO_STATS_REPLY if is_empty_nutrition(totals) else replies.daily_stats(totals)
        return state

    async def _fallback_node(self, state: AgentState) -> AgentState:
        state["reply"] = replies.FALLBACK_REPLY
        return state

    async def _rejected_node(self, state: AgentState) -> AgentState:
        state["reply"] = replies.REJECTED_REPLY
        return state

    @staticmethod
    def _route_after_validation(state: AgentState) -> str:
        return "orchestrator" if state["approved"] else "rejected"

    @staticmethod
    def _route_by_intent(state: AgentState) -> Intent:
        return state["intent"]

    def _route_after_extract(self, state: AgentState) -> str:
        if state["products"]:
            return "save_meal"
        if state["attempts"] < self._max_attempts:
            return "extract"
        return "extract_failed"

    def _build(self):
        builder = StateGraph(AgentState)
        builder.add_node("validate", self._validate_node)
        builder.add_node("orchestrator", self._orchestrator_node)
        builder.add_node("extract", self._extract_node)
        builder.add_node("save_meal", self._save_meal_node)
        builder.add_node("extract_failed", self._extract_failed_node)
        builder.add_node("get_stats", self._get_stats_node)
        builder.add_node("fallback", self._fallback_node)
        builder.add_node("rejected", self._rejected_node)

        builder.add_edge(START, "validate")
        builder.add_conditional_edges(
            "validate",
            self._route_after_validation,
            {"orchestrator": "orchestrator", "rejected": "rejected"},
        )
        builder.add_conditional_edges(
            "orchestrator",
            self._route_by_intent,
            {
                Intent.LOG_FOOD: "extract",
                Intent.GET_STATS: "get_stats",
                Intent.UNKNOWN: "fallback",
            },
        )
        builder.add_conditional_edges(
            "extract",
            self._route_after_extract,
            {"save_meal": "save_meal", "extract": "extract", "extract_failed": "extract_failed"},
        )
        builder.add_edge("save_meal", END)
        builder.add_edge("extract_failed", END)
        builder.add_edge("get_stats", END)
        builder.add_edge("fallback", END)
        builder.add_edge("rejected", END)

        return builder.compile()

    @traceable(name="consumption_agent")
    async def run(self, user_id: int, message: str) -> str:
        initial_state: AgentState = {
            "user_id": user_id,
            "message": message,
            "approved": False,
            "intent": Intent.UNKNOWN,
            "products": None,
            "attempts": 0,
            "reply": "",
        }
        final_state = await self._compiled.ainvoke(initial_state)
        return final_state["reply"]
