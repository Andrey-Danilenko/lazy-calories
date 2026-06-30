from telegram import Update
from telegram.ext import ContextTypes

from src.common.logger import log_action

WELCOME_MESSAGE = """Привет!
Напиши мне, что ты съел, и я запишу полученные КБЖУ.
Спроси, сколько ты съел сегодня, и я подсчитаю КБЖУ за все твои сегодняшние приёмы пищи."""


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log_action(update, "команда /start")
    await context.bot.send_message(chat_id=update.effective_chat.id, text=WELCOME_MESSAGE)
