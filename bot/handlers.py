import io
import logging
import os
import urllib.parse
from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    BufferedInputFile,
    InlineQuery,
    InlineQueryResultPhoto,
    InlineQueryResultArticle,
    InputTextMessageContent
)

from bot.meme_maker import generate_meme, get_template_names

router = Router()
logger = logging.getLogger(__name__)

# Render URL or fallback
PUBLIC_URL = os.getenv("RENDER_EXTERNAL_URL") or os.getenv("PUBLIC_URL") or "https://memeyturok.onrender.com"
# Strip trailing slash if present
PUBLIC_URL = PUBLIC_URL.rstrip("/")


def clean_mention(text: str, bot_username: str | None) -> str:
    """Removes @bot_username tag from the caption text."""
    if not text:
        return ""
    if bot_username:
        words = text.split()
        filtered = [w for w in words if not w.lower().startswith(f"@{bot_username.lower()}")]
        return " ".join(filtered).strip()
    return text.strip()


@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot):
    bot_info = await bot.get_me()
    username = bot_info.username or "bot"
    text = (
        "👋 **Привет! Я бот для создания мемов с классическим шрифтом Impact.**\n\n"
        "✨ **3 способа использовать бота:**\n\n"
        "1️⃣ **В любой личке / переписке (Инлайн-режим как @pic):**\n"
        f"   Напиши в поле ввода: `@{username} ТЕКСТ МЕМА`\n"
        "   (или `ТЕКСТ СВЕРХУ; ТЕКСТ СНИЗУ`) — выбери мем из всплывающего списка и отправь другу!\n\n"
        "2️⃣ **В личке со мной:**\n"
        "   Отправь/перешли картинку с текстом или ответь текстом на картинку.\n\n"
        "3️⃣ **В групповых чатах:**\n"
        f"   Ответь (Reply) на любую картинку: `@{username} Текст мема`\n\n"
        "💡 *Совет: Используй точку с запятой `;` или перенос строки, чтобы разделить текст на верх и низ.*"
    )
    await message.answer(text, parse_mode="Markdown")


@router.message(Command("help"))
async def cmd_help(message: Message, bot: Bot):
    await cmd_start(message, bot)


@router.inline_query()
async def handle_inline_query(inline_query: InlineQuery, bot: Bot):
    """
    Handles inline requests in any chat (e.g. `@memeyturokbot когда написал код; и он заработал`).
    Returns live meme previews generated on the fly.
    """
    query_text = inline_query.query.strip()
    templates = get_template_names()

    if not query_text:
        results = [
            InlineQueryResultArticle(
                id="help_hint",
                title="✍️ Напишите текст мема",
                description="Пример: @memeyturokbot Текст сверху; Текст снизу",
                input_message_content=InputTextMessageContent(
                    message_text="Чтобы сделать мем, напишите: `@memeyturokbot Текст мема`",
                    parse_mode="Markdown"
                )
            )
        ]
        await inline_query.answer(results, cache_time=5, is_personal=True)
        return

    results = []
    encoded_text = urllib.parse.quote(query_text)

    # Names mapping for pretty titles in Russian
    template_titles = {
        "drake": "Дрейк (Drake)",
        "rollsafe": "Умный парень (Roll Safe)",
        "doge": "Доге (Doge)",
        "fine": "This is Fine (Собака в огне)",
        "spongebob": "Спанч Боб (SpongeBob)",
        "disastergirl": "Девочка с пожаром (Disaster Girl)",
        "fry": "Фрай подозрительный (Fry Futurama)",
        "grumpycat": "Сердитый Кот (Grumpy Cat)",
        "buzz": "Базз Лайтер (Buzz Everywhere)"
    }

    for idx, t_name in enumerate(templates):
        img_url = f"{PUBLIC_URL}/meme_img?t={t_name}&q={encoded_text}"
        title = template_titles.get(t_name, t_name.capitalize())
        
        results.append(
            InlineQueryResultPhoto(
                id=f"meme_{t_name}_{idx}",
                photo_url=img_url,
                thumbnail_url=img_url,
                caption="",
                title=title
            )
        )

    await inline_query.answer(results, cache_time=10, is_personal=True)


@router.message(F.photo, F.caption)
async def handle_photo_with_caption(message: Message, bot: Bot):
    """Handles direct photo upload with caption."""
    bot_info = await bot.get_me()
    caption = clean_mention(message.caption or "", bot_info.username)
    if not caption:
        return

    await process_meme_request(
        message=message,
        bot=bot,
        photo_file_id=message.photo[-1].file_id,
        caption=caption
    )


@router.message(F.reply_to_message)
async def handle_reply(message: Message, bot: Bot):
    """Handles reply to a message containing photo or image document."""
    reply = message.reply_to_message
    if not reply:
        return

    raw_text = message.text or message.caption or ""
    bot_info = await bot.get_me()
    caption = clean_mention(raw_text, bot_info.username)
    
    if not caption:
        return

    if reply.photo:
        await process_meme_request(
            message=message,
            bot=bot,
            photo_file_id=reply.photo[-1].file_id,
            caption=caption
        )
        return

    if reply.document and reply.document.mime_type and reply.document.mime_type.startswith("image/"):
        await process_meme_request(
            message=message,
            bot=bot,
            photo_file_id=reply.document.file_id,
            caption=caption
        )
        return


async def process_meme_request(
    message: Message,
    bot: Bot,
    photo_file_id: str,
    caption: str
):
    """Downloads image, overlays meme text, and sends back the result."""
    try:
        await bot.send_chat_action(chat_id=message.chat.id, action="upload_photo")

        file_info = await bot.get_file(photo_file_id)
        if not file_info.file_path:
            await message.reply("❌ Не удалось получить файл изображения.")
            return

        file_bytes_io = io.BytesIO()
        await bot.download_file(file_info.file_path, destination=file_bytes_io)
        input_bytes = file_bytes_io.getvalue()

        output_bytes = generate_meme(input_bytes, caption)

        meme_file = BufferedInputFile(output_bytes, filename="meme.jpg")
        await message.reply_photo(photo=meme_file)

    except Exception as e:
        logger.exception("Error processing meme request: %s", e)
        await message.reply("⚠️ Ошибка при создании мема. Проверьте формат картинки.")
