import io
from PIL import Image
from bot.meme_maker import generate_meme

def test_meme_generation():
    # Create a test background image (600x600 orange-ish background)
    img = Image.new("RGB", (800, 600), color=(50, 100, 150))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    img_bytes = buf.getvalue()

    # Test 1: Top and bottom Russian text
    caption_1 = "КОГДА НАПИСАЛ КОД; И ОН СРАЗУ ЗАРАБОТАЛ"
    out_1 = generate_meme(img_bytes, caption_1)
    with open("test_meme_1.jpg", "wb") as f:
        f.write(out_1)
    print("Test 1 passed: test_meme_1.jpg created (size:", len(out_1), "bytes)")

    # Test 2: Single long text at the bottom with multiline wrap
    caption_2 = "ЭТО ТЕСТОВЫЙ ОЧЕНЬ ДЛИННЫЙ ТЕКСТ ДЛЯ ПРОВЕРКИ АВТОМАТИЧЕСКОГО ПЕРЕНОСА СТРОК И МАСШТАБИРОВАНИЯ МЕМНОГО ШРИФТА"
    out_2 = generate_meme(img_bytes, caption_2)
    with open("test_meme_2.jpg", "wb") as f:
        f.write(out_2)
    print("Test 2 passed: test_meme_2.jpg created (size:", len(out_2), "bytes)")

if __name__ == "__main__":
    test_meme_generation()
