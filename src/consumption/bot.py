from collections.abc import Callable

from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession
from telegram import Update
from telegram.ext import ContextTypes

from src.common.logger import log_action
from src.common.prompts_validator import PromptValidator
from src.consumption.agent import ConsumptionAgent
from src.consumption.graph import ConsumptionGraph
from src.consumption.resolver import NutritionResolver
from src.consumption.storage import MealRepository
from src.consumption.vector_store import FoodVectorStore


def make_message_handler(
    session_factory: async_sessionmaker[AsyncSession], get_vector_store: Callable[[], FoodVectorStore | None]
):
    agent = ConsumptionAgent()
    graph = ConsumptionGraph(agent, MealRepository(session_factory), PromptValidator())

    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text.strip()
        log_action(update, f"текстовое сообщение: {text}")

        vector_store = get_vector_store()
        if vector_store is None:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Бот ещё не готов, попробуйте позже")
            return

        resolver = NutritionResolver(agent, vector_store)
        reply = await graph.run(update.effective_user.id, text, resolver)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=reply)

    return handle_message
