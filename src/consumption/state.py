from typing import TypedDict

from src.consumption.intents import Intent


class AgentState(TypedDict):
    user_id: int
    message: str
    approved: bool
    intent: Intent
    products: list[dict] | None
    attempts: int
    reply: str
