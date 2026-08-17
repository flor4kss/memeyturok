import asyncio
import os
import qrcode
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError

API_ID = 2040
API_HASH = "b18441a1ff607e10a989891a5462e627"

async def generate():
    client = TelegramClient(
        StringSession(),
        API_ID,
        API_HASH,
        device_model="Windows PC",
        system_version="Windows 10",
        app_version="5.2.3 x64",
        lang_code="ru"
    )
    await client.connect()

    qr_login = await client.qr_login()
    print("\n" + "=" * 60)
    print("📲 ГЕНЕРАЦИЯ СВЕЖЕЙ СЕССИИ ДЛЯ RENDER")
    print("=" * 60)
    print("1. Открой Telegram на телефоне: Настройки -> Устройства -> Подключить устройство")
    print("2. Отсканируй QR-код ниже:")
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

    print("\nКартинка QR-кода также сохранена в файл: login_qr.png")
    print("Ожидание сканирования...")

    try:
        await qr_login.wait(timeout=120)
    except SessionPasswordNeededError:
        password = input("Введите пароль двухфакторной аутентификации (2FA): ")
        await client.sign_in(password=password)

    session_str = client.session.save()
    
    with open("session_string.txt", "w", encoding="utf-8") as f:
        f.write(session_str)

    print("\n" + "=" * 60)
    print("✅ СВЕЖАЯ СЕССИЯ УСПЕШНО СОЗДАНА И СОХРАНЕНА В session_string.txt!")
    print("=" * 60)
    print(session_str)
    print("=" * 60 + "\n")

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(generate())
