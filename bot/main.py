import asyncio
import logging
import os
import sys
from aiohttp import web
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

from bot.handlers import router
from bot.meme_maker import generate_meme, get_template_bytes

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", "8080"))


async def health_check_handler(request: web.Request) -> web.Response:
    """Simple health check endpoint for Render / Web Service hosting."""
    return web.json_response({
        "status": "online",
        "service": "telegram-meme-bot"
    })


async def meme_image_handler(request: web.Request) -> web.Response:
    """Dynamically generates and returns meme image for inline Telegram queries."""
    template = request.query.get("t", "drake")
    text = request.query.get("q", "")

    img_bytes = get_template_bytes(template)
    if not img_bytes:
        img_bytes = get_template_bytes("drake")
    
    if not img_bytes:
        return web.Response(status=404, text="Template not found")

    try:
        result_bytes = generate_meme(img_bytes, text)
        return web.Response(
            body=result_bytes,
            content_type="image/jpeg",
            headers={"Cache-Control": "public, max-age=86400"}
        )
    except Exception as e:
        logging.error(f"Error generating inline meme: {e}")
        return web.Response(status=500, text="Internal Error")


async def start_web_server():
    """Starts HTTP server for health-checks and dynamic inline meme generation."""
    app = web.Application()
    app.router.add_get("/", health_check_handler)
    app.router.add_get("/health", health_check_handler)
    app.router.add_get("/meme_img", meme_image_handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logging.info(f"HTTP server (Health & Inline Memes) started on port {PORT}")


async def main():
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

    try:
        await start_web_server()
    except Exception as e:
        logging.warning(f"Could not start HTTP server: {e}")

    logging.info("Starting Telegram Meme Bot (polling & inline mode)...")
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped.")
