import asyncio
import logging
import os
import sys
from aiohttp import web
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

from bot.handlers import router

# Load .env file if present
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", "8080"))


async def health_check_handler(request: web.Request) -> web.Response:
    """Simple health check endpoint for Render / Web Service hosting."""
    return web.json_response({
        "status": "online",
        "service": "telegram-meme-bot"
    })


async def start_web_server():
    """Starts a minimal HTTP server so Render Web Service marks the deployment as Healthy."""
    app = web.Application()
    app.router.add_get("/", health_check_handler)
    app.router.add_get("/health", health_check_handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logging.info(f"Health check HTTP server started on port {PORT}")


async def main():
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    if not BOT_TOKEN:
        logging.error("ERROR: BOT_TOKEN is not set! Please set it in .env or Render environment variables.")
        sys.exit(1)

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    # Start health check server if running on Render / web environment
    try:
        await start_web_server()
    except Exception as e:
        logging.warning(f"Could not start HTTP health check server: {e}")

    logging.info("Starting Telegram Meme Bot (polling)...")
    
    # Drop pending updates to avoid spam upon startup
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped.")
