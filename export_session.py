import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession

API_ID = 2040
API_HASH = "b18441a1ff607e10a989891a5462e627"

async def export():
    client = TelegramClient("userbot_session", API_ID, API_HASH)
    await client.connect()
    
    if not await client.is_user_authorized():
        print("Session not authorized. Run python userbot.py first!")
        return

    string_session = StringSession.save(client.session)
    print("\n" + "=" * 60)
    print("YOUR SESSION_STRING FOR RENDER:")
    print("=" * 60)
    print(string_session)
    print("=" * 60 + "\n")

    # Save to a text file for easy copy-pasting
    with open("session_string.txt", "w", encoding="utf-8") as f:
        f.write(string_session)
    print("Saved to session_string.txt")

if __name__ == "__main__":
    asyncio.run(export())
