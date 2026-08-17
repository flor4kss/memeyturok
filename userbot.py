import asyncio
import io
import logging
import os
import sys
from pathlib import Path
import qrcode
from aiohttp import web
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError

from bot.meme_maker import generate_meme

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("Userbot")

API_ID = int(os.getenv("TELEGRAM_API_ID", "2040"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "b18441a1ff607e10a989891a5462e627")
SESSION_STRING = os.getenv("SESSION_STRING")
PORT = int(os.getenv("PORT", "8080"))

# Initialize Client: StringSession for Render cloud, file session for local
if SESSION_STRING:
    session = StringSession(SESSION_STRING)
else:
    session = "userbot_session"

client = TelegramClient(
    session,
    API_ID,
    API_HASH,
    device_model="Windows PC",
    system_version="Windows 10",
    app_version="5.2.3 x64",
    lang_code="ru"
)

COMMAND_PREFIXES = (".м ", ".m ", ".meme ", ".мем ")


@client.on(events.NewMessage(outgoing=True))
async def handle_meme_command(event: events.NewMessage.Event):
    text = event.raw_text or ""
    
    matched_prefix = None
    for prefix in COMMAND_PREFIXES:
        if text.lower().startswith(prefix):
            matched_prefix = prefix
            break

    if not matched_prefix:
        return

    meme_caption = text[len(matched_prefix):].strip()
    if not meme_caption:
        status_msg = await event.edit("⚠️ Укажите текст мема, например: `.м Текст мема`")
        await asyncio.sleep(3)
        await status_msg.delete()
        return

    if not event.is_reply:
        status_msg = await event.edit("⚠️ Ответьте (Reply) этой командой на картинку!")
        await asyncio.sleep(3)
        await status_msg.delete()
        return

    reply_msg = await event.get_reply_message()
    if not reply_msg or not (reply_msg.photo or reply_msg.document or reply_msg.sticker):
        status_msg = await event.edit("⚠️ Сообщение, на которое вы ответили, не содержит картинки!")
        await asyncio.sleep(3)
        await status_msg.delete()
        return

    await event.edit("⏳ *Создаю мем...*", parse_mode="Markdown")

    try:
        buffer = io.BytesIO()
        await client.download_media(reply_msg, file=buffer)
        image_bytes = buffer.getvalue()

        if not image_bytes:
            raise ValueError("Не удалось скачать картинку")

        meme_bytes = generate_meme(image_bytes, meme_caption)
        
        meme_io = io.BytesIO(meme_bytes)
        meme_io.name = "meme.jpg"

        await client.send_file(
            entity=event.chat_id,
            file=meme_io,
            reply_to=reply_msg.id
        )

        await event.delete()
        logger.info(f"Мем успешно отправлен в чат {event.chat_id}")

    except Exception as e:
        logger.exception("Ошибка при создании мема: %s", e)
        error_msg = await event.edit(f"❌ Ошибка: {e}")
        await asyncio.sleep(3)
        await error_msg.delete()


async def health_check_handler(request: web.Request) -> web.Response:
    return web.json_response({"status": "online", "service": "telegram-meme-userbot"})


async def start_web_server():
    """Lightweight server for Render Health Checks"""
    app = web.Application()
    app.router.add_get("/", health_check_handler)
    app.router.add_get("/health", health_check_handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"Health check HTTP server started on port {PORT}")


async def login_with_qr():
    qr_login = await client.qr_login()
    print("\n" + "=" * 60)
    print("📲 ВХОД ЧЕРЕЗ QR-КОД (БЕЗ SMS И КАПЧИ)")
    print("=" * 60)
    print("1. Открой Telegram на телефоне.")
    print("2. Перейди: Настройки -> Устройства -> Подключить устройство")
    print("3. Наведи камеру на QR-код ниже:")
    print("=" * 60 + "\n")

    qr = qrcode.QRCode(border=1)
    qr.add_data(qr_login.url)
    qr.make(fit=True)
    
    qr_img = qr.make_image(fill_color="black", back_color="white")
    qr_img.save("login_qr.png")
    
    try:
        qr.print_ascii(invert=True)
    except Exception:
        pass

    print("\n💡 Картинка с QR-кодом также сохранена в файл: login_qr.png")
    print(f"🔗 Или скопируйте ссылку: {qr_login.url}\n")
    print("⏳ Ожидание сканирования...")

    try:
        await qr_login.wait(timeout=120)
    except SessionPasswordNeededError:
        password = input("Введите пароль двухфакторной аутентификации (2FA): ")
        await client.sign_in(password=password)


async def main():
    # Start health check server for Render Web Service
    try:
        await start_web_server()
    except Exception as e:
        logger.warning(f"Could not start HTTP server: {e}")

    await client.connect()
    
    if not await client.is_user_authorized():
        if SESSION_STRING:
            print("❌ Ошибка: SESSION_STRING недействительна или устарела.")
            sys.exit(1)
        await login_with_qr()

    if os.path.exists("login_qr.png"):
        try:
            os.remove("login_qr.png")
        except Exception:
            pass

    me = await client.get_me()
    print("\n" + "=" * 60)
    print(f"✅ Юзербот успешно запущен под аккаунтом: {me.first_name} (@{me.username})")
    print("💡 Как пользоваться прямо в переписке:")
    print("   1. Зайди в любую личку в Telegram.")
    print("   2. Ответь (Reply) на любую картинку: .м Твой текст")
    print("=" * 60)
    print("🔥 Юзербот активен в реальном времени!\n")
    
    await client.run_until_disconnected()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("\nЮзербот остановлен.")
