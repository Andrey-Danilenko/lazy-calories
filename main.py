from telegram.ext import ApplicationBuilder
from telegram.ext import CommandHandler
from telegram.ext import filters
from telegram.ext import MessageHandler

from src.common.config import settings
from src.common.start import start
from src.consumption.bot import make_message_handler


def build_application():
    application = ApplicationBuilder().token(settings.telegram_token).concurrent_updates(True).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), make_message_handler()))
    return application


def main():
    application = build_application()
    application.run_polling()


if __name__ == "__main__":
    print("Starting bot...")
    main()
