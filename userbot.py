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
from telethon.errors import SessionPasswordNeededError, FloodWaitError

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
from bot.ai_helper import query_groq

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

WHITELIST_USERNAMES = ["vextert"]
extra_users = os.getenv("WHITELIST_USERS", "")
if extra_users:
    WHITELIST_USERNAMES.extend([u.strip().lstrip("@").lower() for u in extra_users.split(",") if u.strip()])

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

EN_TO_RU = str.maketrans(
    "`qwertyuiop[]asdfghjkl;'zxcvbnm,./~QWERTYUIOP{}ASDFGHJKL:\"ZXCVBNM<>?@",
    "ёйцукенгшщзхъфывапролджэячсмитьбю.ЁЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭЯЧСМИТЬБЮ,@\""
)
RU_TO_EN = str.maketrans(
    "ёйцукенгшщзхъфывапролджэячсмитьбю.ЁЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭЯЧСМИТЬБЮ,",
    "`qwertyuiop[]asdfghjkl;'zxcvbnm,./~QWERTYUIOP{}ASDFGHJKL:\"ZXCVBNM<>?"
)


def switch_layout(text: str) -> str:
    cyrillic_chars = sum(1 for c in text if 'а' <= c.lower() <= 'я' or c.lower() == 'ё')
    latin_chars = sum(1 for c in text if 'a' <= c.lower() <= 'z')
    if cyrillic_chars > latin_chars:
        return text.translate(RU_TO_EN)
    else:
        return text.translate(EN_TO_RU)


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

    # -------------------------------------------------------------
    # 1. AI ПЕРСОНАЖИ И НЕЙРОСЕТЬ (GROQ / LLAMA 3.3)
    # -------------------------------------------------------------
    ai_role = None
    ai_header = ""
    ai_query = ""
    is_clean_mode = False

    # Check for clean/stealth mode prefix (e.g. .патрик- or .ии-)
    # Character commands list: (prefixes, role, header)
    ai_definitions = [
        ([".патрик-", ".patrick-"], "patrick", "⭐️ **Патрик Стар:**", True),
        ([".патрик", ".patrick"], "patrick", "⭐️ **Патрик Стар:**", False),
        ([".стоун-", ".сэнку-", ".stone-"], "stone", "🧪 **Сэнку (Dr. Stone):**", True),
        ([".стоун", ".сэнку", ".сенку", ".stone"], "stone", "🧪 **Сэнку (Dr. Stone):**", False),
        ([".стэтхем-", ".statham-"], "statham", "🐺 **Джейсон Стэтхем:**", True),
        ([".стэтхем", ".стетхем", ".statham"], "statham", "🐺 **Джейсон Стэтхем:**", False),
        ([".гопник-", ".пацан-"], "gopnik", "🧢 **Пацанчик с района:**", True),
        ([".гопник", ".пацан"], "gopnik", "🧢 **Пацанчик с района:**", False),
        ([".бабка-", ".дед-"], "babka", "👵 **Бабка у подъезда:**", True),
        ([".бабка", ".дед"], "babka", "👵 **Бабка у подъезда:**", False),
        ([".кратко-", ".суть-", ".tldr-"], "summary", "📋 **Краткая суть:**", True),
        ([".кратко", ".суть", ".tldr"], "summary", "📋 **Краткая суть:**", False),
        ([".ии- ", ".жпт- ", ".ai- ", ".gpt- "], "default", "🤖 **AI-Ответ (Groq):**", True),
        ([".ии ", ".жпт ", ".ai ", ".gpt ", ".ии\n", ".жпт\n"], "default", "🤖 **AI-Ответ (Groq):**", False),
    ]

    for prefixes, role, header, clean in ai_definitions:
        for p in prefixes:
            if lower_text == p.strip() or lower_text.startswith(p if p.endswith(" ") or p.endswith("\n") or p.endswith("-") else p + " "):
                ai_role = role
                ai_header = header
                is_clean_mode = clean
                # Extract query after prefix
                ai_query = text[len(p.strip()):].strip()
                break
        if ai_role:
            break

    if ai_role:
        if not await is_authorized_sender(event):
            return

        context = ""
        if event.is_reply:
            reply_msg = await event.get_reply_message()
            if reply_msg and reply_msg.text:
                context = reply_msg.text

        if not ai_query and not context:
            hint = "⚠️ Задайте вопрос или ответьте на сообщение этой командой!"
            if event.out:
                msg = await event.edit(hint)
                await asyncio.sleep(3)
                await msg.delete()
            else:
                await event.reply(hint)
            return

        if event.out:
            msg_to_edit = await event.edit("🧠 *Генерирую...*" if not is_clean_mode else "...")
        else:
            msg_to_edit = await event.reply("🧠 *Генерирую...*" if not is_clean_mode else "...")

        prompt = ai_query or "Отреагируй на сообщение выше в своем характере."
        answer = await query_groq(user_prompt=prompt, system_role=ai_role, context_text=context)

        # Clean mode sends purely the AI text without headers or dividers
        if is_clean_mode:
            formatted_response = answer
        else:
            formatted_response = (
                f"{ai_header}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"{answer}\n"
                f"━━━━━━━━━━━━━━━━━━"
            )

        try:
            await msg_to_edit.edit(formatted_response, parse_mode="Markdown")
        except Exception:
            await msg_to_edit.edit(formatted_response)
        return

    # -------------------------------------------------------------
    # 2. АНИМАЦИЯ ПЕЧАТИ: .тайп <текст> / .type <текст>
    # -------------------------------------------------------------
    for prefix in [".тайп ", ".type "]:
        if lower_text.startswith(prefix):
            if not await is_authorized_sender(event):
                return
            target_text = text[len(prefix):].strip()
            if not target_text:
                return

            msg_to_edit = event if event.out else await event.reply("▌")
            step = 2 if len(target_text) > 30 else 1
            for i in range(0, len(target_text), step):
                current_str = target_text[:i + step]
                try:
                    await msg_to_edit.edit(current_str + "▌")
                    await asyncio.sleep(0.06)
                except FloodWaitError as fwe:
                    await asyncio.sleep(fwe.seconds)
                except Exception:
                    pass

            try:
                await msg_to_edit.edit(target_text)
            except Exception:
                pass
            return

    # -------------------------------------------------------------
    # 3. АНИМАЦИЯ ВЗЛОМА: .взлом <цель>
    # -------------------------------------------------------------
    for prefix in [".взлом", ".hack", ".хак"]:
        if lower_text == prefix or lower_text.startswith(prefix + " "):
            if not await is_authorized_sender(event):
                return
            target = text[len(prefix):].strip() or "Пентагона"
            msg_to_edit = event if event.out else await event.reply("⏳ Запуск взлома...")
            stages = [
                f"💻 [░░░░░░░░░░] 0% Подключение к спутникам...",
                f"📡 [██░░░░░░░░] 20% Поиск уязвимостей {target}...",
                f"🔑 [████░░░░░░] 45% Обход двухфакторной защиты...",
                f"📥 [██████░░░░] 65% Скачивание секретных переписок...",
                f"💾 [████████░░] 85% Загрузка компромата в облако...",
                f"☠️ [██████████] 100% Взлом {target} успешно завершён!\n\n⚠️ **Результат:** Найдено 1488 гигабайт папок с мемами."
            ]
            for stage in stages:
                try:
                    await msg_to_edit.edit(stage)
                    await asyncio.sleep(0.7)
                except Exception:
                    pass
            return

    # -------------------------------------------------------------
    # 4. АНИМАЦИЯ СЕРДЕЦ: .сердце / .love
    # -------------------------------------------------------------
    if lower_text in [".сердце", ".love", ".любовь"]:
        if not await is_authorized_sender(event):
            return
        msg_to_edit = event if event.out else await event.reply("🖤")
        hearts = ["🖤", "💜", "💙", "💚", "💛", "🧡", "❤️", "💖", "✨ С любовью! ✨"]
        for h in hearts:
            try:
                await msg_to_edit.edit(h)
                await asyncio.sleep(0.35)
            except Exception:
                pass
        return

    # -------------------------------------------------------------
    # 5. ИСПРАВЛЕНИЕ РАСКЛАДКИ: .р / .раскладка
    # -------------------------------------------------------------
    if lower_text in [".р", ".раскладка", ".layout", ".switch"]:
        if not await is_authorized_sender(event):
            return
        if not event.is_reply:
            hint = await (event.edit("⚠️ Ответьте на сообщение, чтобы исправить его раскладку!") if event.out else event.reply("⚠️ Ответьте на сообщение!"))
            await asyncio.sleep(3)
            await hint.delete()
            return
            
        reply_msg = await event.get_reply_message()
        if not reply_msg or not reply_msg.text:
            return
            
        fixed_text = switch_layout(reply_msg.text)
        res_str = f"🔄 **Исправленная раскладка:**\n━━━━━━━━━━━━━━━━━━\n{fixed_text}\n━━━━━━━━━━━━━━━━━━"
        if event.out:
            await event.edit(res_str, parse_mode="Markdown")
        else:
            await event.reply(res_str, parse_mode="Markdown")
        return

    # -------------------------------------------------------------
    # 6. ГЕНЕРАТОРЫ МЕМОВ (ТРЕБУЮТ РЕПЛАЙ НА КАРТИНКУ)
    # -------------------------------------------------------------
    command_type = None
    payload = ""

    for prefix in [".м ", ".m ", ".meme ", ".мем ", ".м\n", ".m\n"]:
        if lower_text.startswith(prefix):
            command_type = "meme"
            payload = text[len(prefix):].strip()
            break

    if not command_type:
        for prefix in [".дем ", ".dem ", ".дем\n", ".dem\n"]:
            if lower_text.startswith(prefix):
                command_type = "demotivator"
                payload = text[len(prefix):].strip()
                break

    if not command_type:
        for prefix in [".волк ", ".цитата "]:
            if lower_text.startswith(prefix):
                command_type = "wolf"
                payload = text[len(prefix):].strip()
                break

    if not command_type:
        for prefix in [".новости ", ".news "]:
            if lower_text.startswith(prefix):
                command_type = "news"
                payload = text[len(prefix):].strip()
                break

    if not command_type:
        for cmd in [".шакал", ".дипфрай", ".fry", ".жарить"]:
            if lower_text == cmd or lower_text.startswith(cmd + " "):
                command_type = "deepfry"
                break

    if not command_type:
        for cmd in [".бабл", ".bubble"]:
            if lower_text == cmd or lower_text.startswith(cmd + " "):
                command_type = "bubble"
                break

    if not command_type:
        for cmd in [".лево", ".left"]:
            if lower_text == cmd or lower_text.startswith(cmd + " "):
                command_type = "symmetry_left"
                break

    if not command_type:
        for cmd in [".право", ".right"]:
            if lower_text == cmd or lower_text.startswith(cmd + " "):
                command_type = "symmetry_right"
                break

    if not command_type:
        for cmd in [".рип", ".rip", ".память"]:
            if lower_text == cmd or lower_text.startswith(cmd + " "):
                command_type = "rip"
                break

    if not command_type:
        return

    if not await is_authorized_sender(event):
        return

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
    print("🧠 AI Персонажи: .патрик, .стоун, .стэтхем, .гопник, .бабка, .кратко, .ии")
    print("🤫 Чистый режим без плашек: .патрик-, .стоун-, .ии-")
    print("=" * 60)
    print("🔥 Юзербот активен в реальном времени!\n")
    
    await client.run_until_disconnected()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("\nЮзербот остановлен.")
