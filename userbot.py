import asyncio
import io
import logging
import os
import sys
from pathlib import Path
from aiohttp import web
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError

from bot.meme_maker import (
    generate_meme,
    generate_demotivator,
    generate_deepfry,
    generate_speech_bubble,
    generate_symmetry,
    generate_wolf_quote,
    generate_rip,
    generate_breaking_news
)

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

# Whitelisted usernames (without @)
WHITELIST_USERNAMES = ["vextert"]
extra_users = os.getenv("WHITELIST_USERS", "")
if extra_users:
    WHITELIST_USERNAMES.extend([u.strip().lstrip("@").lower() for u in extra_users.split(",") if u.strip()])

# Initialize Client
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


async def is_authorized_sender(event: events.NewMessage.Event) -> bool:
    if event.out:
        return True
    if event.is_private:
        return True

    sender = await event.get_sender()
    if not sender:
        return False

    username = (getattr(sender, "username", None) or "").lower()
    if username in WHITELIST_USERNAMES:
        return True

    return False


@client.on(events.NewMessage())
async def handle_commands(event: events.NewMessage.Event):
    text = (event.raw_text or "").strip()
    if not text:
        return

    lower_text = text.lower()
    
    command_type = None
    payload = ""

    # 1. Classic Impact Meme: .м, .m, .meme, .мем
    for prefix in [".м ", ".m ", ".meme ", ".мем ", ".м\n", ".m\n"]:
        if lower_text.startswith(prefix):
            command_type = "meme"
            payload = text[len(prefix):].strip()
            break

    # 2. Demotivator: .дем, .dem
    if not command_type:
        for prefix in [".дем ", ".dem ", ".дем\n", ".dem\n"]:
            if lower_text.startswith(prefix):
                command_type = "demotivator"
                payload = text[len(prefix):].strip()
                break

    # 3. Wolf Quote: .волк, .цитата, .стэтхем, .стетхем
    if not command_type:
        for prefix in [".волк ", ".цитата ", ".стэтхем ", ".стетхем ", ".волк\n", ".цитата\n"]:
            if lower_text.startswith(prefix):
                command_type = "wolf"
                payload = text[len(prefix):].strip()
                break

    # 4. Breaking News: .новости, .news
    if not command_type:
        for prefix in [".новости ", ".news ", ".новости\n", ".news\n"]:
            if lower_text.startswith(prefix):
                command_type = "news"
                payload = text[len(prefix):].strip()
                break

    # 5. Deep Fry / Шакализатор: .шакал, .дипфрай, .fry, .жарить
    if not command_type:
        for cmd in [".шакал", ".дипфрай", ".fry", ".жарить"]:
            if lower_text == cmd or lower_text.startswith(cmd + " ") or lower_text.startswith(cmd + "\n"):
                command_type = "deepfry"
                break

    # 6. Speech Bubble: .бабл, .bubble
    if not command_type:
        for cmd in [".бабл", ".bubble"]:
            if lower_text == cmd or lower_text.startswith(cmd + " ") or lower_text.startswith(cmd + "\n"):
                command_type = "bubble"
                break

    # 7. Symmetry Left: .лево, .left
    if not command_type:
        for cmd in [".лево", ".left"]:
            if lower_text == cmd or lower_text.startswith(cmd + " "):
                command_type = "symmetry_left"
                break

    # 8. Symmetry Right: .право, .right
    if not command_type:
        for cmd in [".право", ".right"]:
            if lower_text == cmd or lower_text.startswith(cmd + " "):
                command_type = "symmetry_right"
                break

    # 9. RIP / Mourning: .рип, .rip, .память
    if not command_type:
        for cmd in [".рип", ".rip", ".память"]:
            if lower_text == cmd or lower_text.startswith(cmd + " "):
                command_type = "rip"
                break

    # If no command matched, ignore
    if not command_type:
        return

    # Check authorization
    if not await is_authorized_sender(event):
        return

    logger.info(f"Обработка команды '{command_type}' от {'владельца' if event.out else 'друга'}")

    # Check if message is a reply
    if not event.is_reply:
        if event.out:
            status_msg = await event.edit("⚠️ Ответьте (Reply) этой командой на картинку!")
            await asyncio.sleep(3)
            await status_msg.delete()
        else:
            await event.reply("⚠️ Ответьте (Reply) этой командой на картинку!")
        return

    reply_msg = await event.get_reply_message()
    if not reply_msg or not (reply_msg.photo or reply_msg.document or reply_msg.sticker or reply_msg.media):
        if event.out:
            status_msg = await event.edit("⚠️ Сообщение, на которое вы ответили, не содержит картинки!")
            await asyncio.sleep(3)
            await status_msg.delete()
        else:
            await event.reply("⚠️ Сообщение, на которое вы ответили, не содержит картинки!")
        return

    status_msg = None
    if event.out:
        status_msg = await event.edit("⏳ *Обрабатываю...*", parse_mode="Markdown")

    try:
        buffer = io.BytesIO()
        await client.download_media(reply_msg, file=buffer)
        image_bytes = buffer.getvalue()

        if not image_bytes:
            raise ValueError("Не удалось скачать картинку")

        # Execute chosen effect
        if command_type == "meme":
            if not payload:
                raise ValueError("Укажите текст мема!")
            out_bytes = generate_meme(image_bytes, payload)
        elif command_type == "demotivator":
            if not payload:
                raise ValueError("Укажите текст демотиватора (Заголовок; Подзаголовок)")
            out_bytes = generate_demotivator(image_bytes, payload)
        elif command_type == "wolf":
            if not payload:
                raise ValueError("Укажите текст цитаты!")
            out_bytes = generate_wolf_quote(image_bytes, payload)
        elif command_type == "news":
            out_bytes = generate_breaking_news(image_bytes, payload)
        elif command_type == "deepfry":
            out_bytes = generate_deepfry(image_bytes)
        elif command_type == "bubble":
            out_bytes = generate_speech_bubble(image_bytes)
        elif command_type == "symmetry_left":
            out_bytes = generate_symmetry(image_bytes, side="left")
        elif command_type == "symmetry_right":
            out_bytes = generate_symmetry(image_bytes, side="right")
        elif command_type == "rip":
            out_bytes = generate_rip(image_bytes)
        else:
            return

        out_io = io.BytesIO(out_bytes)
        out_io.name = "result.jpg"

        await event.reply(file=out_io)

        if event.out and status_msg:
            await event.delete()
            
        logger.info(f"Команда {command_type} успешно завершена")

    except Exception as e:
        logger.exception("Ошибка обработки: %s", e)
        if event.out and status_msg:
            error_msg = await event.edit(f"❌ Ошибка: {e}")
            await asyncio.sleep(3)
            await error_msg.delete()
        else:
            await event.reply(f"❌ Ошибка: {e}")


async def health_check_handler(request: web.Request) -> web.Response:
    return web.json_response({"status": "online", "service": "telegram-meme-userbot"})


async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health_check_handler)
    app.router.add_get("/health", health_check_handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"Health check HTTP server started on port {PORT}")


async def login_with_qr():
    try:
        import qrcode
    except ImportError:
        print("Для локального входа установите qrcode: pip install qrcode[pil]")
        sys.exit(1)

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
    print("👥 Доступен для вас и всех друзей в личках!")
    print("=" * 60)
    print("🔥 Юзербот активен в реальном времени!\n")
    
    await client.run_until_disconnected()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("\nЮзербот остановлен.")
