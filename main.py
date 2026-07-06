from telegram.ext import Application
from telegram.ext import ApplicationBuilder
from telegram.ext import CommandHandler
from telegram.ext import filters
from telegram.ext import MessageHandler

from src.common.config import settings
from src.common.db import create_engine
from src.common.db import create_session_factory
from src.common.db import init_models
from src.common.start import start
from src.consumption.bot import make_message_handler


def build_application():
    engine = create_engine()
    session_factory = create_session_factory(engine)

    async def on_startup(_: Application) -> None:
        await init_models(engine)

    async def on_shutdown(_: Application) -> None:
        await engine.dispose()

    application = (
        ApplicationBuilder()
        .token(settings.telegram_token)
        .concurrent_updates(True)
        .post_init(on_startup)
        .post_shutdown(on_shutdown)
        .build()
    )
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), make_message_handler(session_factory)))
    return application


def main():
    application = build_application()
    application.run_polling()


if __name__ == "__main__":
    print("Starting bot...")
    main()
