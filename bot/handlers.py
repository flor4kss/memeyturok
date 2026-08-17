import io
import logging
from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, BufferedInputFile

from bot.meme_maker import generate_meme

router = Router()
logger = logging.getLogger(__name__)


def clean_mention(text: str, bot_username: str | None) -> str:
    """Removes @bot_username tag from the caption text."""
    if not text:
        return ""
    if bot_username:
        # Case-insensitive replacement of bot username
        words = text.split()
        filtered = [w for w in words if not w.lower().startswith(f"@{bot_username.lower()}")]
        return " ".join(filtered).strip()
    return text.strip()


@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot):
    bot_info = await bot.get_me()
    username = bot_info.username or "bot"
    text = (
        "👋 **Привет! Я бот для создания классических мемов.**\n\n"
        "🖼 **Как мной пользоваться:**\n"
        "1. **В личке:**\n"
        "   • Отправь картинку с подписью (caption)\n"
        "   • Или отправь картинку, а затем ответь на неё (Reply) нужным текстом.\n\n"
        "2. **В группе / канале:**\n"
        f"   • Ответь (Reply) на любую картинку: `@{username} Твой текст`\n\n"
        "💡 **Формат надписи:**\n"
        "• Один текст $\\to$ располагается снизу.\n"
        "• `ТЕКСТ СВЕРХУ; ТЕКСТ СНИЗУ` (через `;` или перенос строки) $\\to$ верхний и нижний текст."
    )
    await message.answer(text, parse_mode="Markdown")


@router.message(Command("help"))
async def cmd_help(message: Message, bot: Bot):
    await cmd_start(message, bot)


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

    # Check if text is provided in the reply
    raw_text = message.text or message.caption or ""
    bot_info = await bot.get_me()
    caption = clean_mention(raw_text, bot_info.username)
    
    if not caption:
        return

    # 1. Target is a Photo
    if reply.photo:
        await process_meme_request(
            message=message,
            bot=bot,
            photo_file_id=reply.photo[-1].file_id,
            caption=caption
        )
        return

    # 2. Target is an Image Document (PNG/JPG file sent as uncompressed doc)
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

        # Download photo into in-memory buffer
        file_info = await bot.get_file(photo_file_id)
        if not file_info.file_path:
            await message.reply("❌ Не удалось получить файл изображения.")
            return

        file_bytes_io = io.BytesIO()
        await bot.download_file(file_info.file_path, destination=file_bytes_io)
        input_bytes = file_bytes_io.getvalue()

        # Generate meme
        output_bytes = generate_meme(input_bytes, caption)

        # Send response photo
        meme_file = BufferedInputFile(output_bytes, filename="meme.jpg")
        await message.reply_photo(photo=meme_file)

    except Exception as e:
        logger.exception("Error processing meme request: %s", e)
        await message.reply("⚠️ Ошибка при создании мема. Проверьте формат картинки.")
