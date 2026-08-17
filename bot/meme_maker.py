import io
import os
import textwrap
from pathlib import Path
from typing import Tuple, Optional, List
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageEnhance, ImageFilter

BASE_DIR = Path(__file__).resolve().parent.parent
FONT_PATH = BASE_DIR / "assets" / "font.ttf"
TIMES_FONT_PATH = BASE_DIR / "assets" / "times.ttf"
TEMPLATES_DIR = BASE_DIR / "assets" / "templates"


def get_template_names() -> List[str]:
    if not TEMPLATES_DIR.exists():
        return []
    return [f.stem for f in TEMPLATES_DIR.glob("*.jpg")]


def get_template_bytes(template_name: str) -> Optional[bytes]:
    file_path = TEMPLATES_DIR / f"{template_name}.jpg"
    if file_path.exists():
        return file_path.read_bytes()
    return None


def get_optimal_font_and_lines(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_width: int,
    max_height: int,
    font_path: str,
    initial_font_size: int,
    min_font_size: int = 14
) -> Tuple[ImageFont.FreeTypeFont, List[str], int]:
    font_size = initial_font_size
    
    while font_size >= min_font_size:
        try:
            font = ImageFont.truetype(font_path, font_size)
        except Exception:
            font = ImageFont.load_default()
            return font, [text], 10

        avg_char_width = max(1, int(font_size * 0.52))
        chars_per_line = max(4, int(max_width / avg_char_width))
        
        wrapped_lines = []
        for raw_line in text.split('\n'):
            if not raw_line.strip():
                continue
            lines = textwrap.wrap(raw_line.strip(), width=chars_per_line)
            if not lines:
                wrapped_lines.append(raw_line.strip())
            else:
                wrapped_lines.extend(lines)

        if not wrapped_lines:
            wrapped_lines = [text]

        total_height = 0
        exceeds_width = False
        line_spacing = int(font_size * 0.15)
        
        for line in wrapped_lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            line_w = bbox[2] - bbox[0]
            line_h = bbox[3] - bbox[1]
            if line_w > max_width:
                exceeds_width = True
                break
            total_height += line_h + line_spacing

        if not exceeds_width and total_height <= max_height:
            return font, wrapped_lines, font_size

        font_size -= 2

    font = ImageFont.truetype(font_path, min_font_size)
    return font, textwrap.wrap(text, width=max(8, int(max_width / (min_font_size * 0.52)))), min_font_size


def draw_text_with_outline(
    draw: ImageDraw.ImageDraw,
    lines: List[str],
    font: ImageFont.FreeTypeFont,
    font_size: int,
    image_width: int,
    y_start: int,
    stroke_ratio: float = 0.08
):
    stroke_width = max(2, int(font_size * stroke_ratio))
    line_spacing = int(font_size * 0.15)
    current_y = y_start

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        x = (image_width - text_w) // 2

        draw.text(
            (x, current_y),
            line,
            font=font,
            fill="white",
            stroke_width=stroke_width,
            stroke_fill="black"
        )
        current_y += text_h + line_spacing


def parse_meme_text(text: str) -> Tuple[Optional[str], Optional[str]]:
    clean_text = text.strip()
    if not clean_text:
        return None, None

    for sep in [";", "\n", "|"]:
        if sep in clean_text:
            parts = clean_text.split(sep, 1)
            top = parts[0].strip().upper()
            bottom = parts[1].strip().upper()
            return (top if top else None), (bottom if bottom else None)

    return None, clean_text.upper()


# -------------------------------------------------------------
# 1. МЕМ С ШРИФТОМ IMPACT (.м / .meme)
# -------------------------------------------------------------
def generate_meme(
    image_bytes: bytes,
    caption: str,
    font_path: Optional[str] = None
) -> bytes:
    if font_path is None:
        font_path = str(FONT_PATH)

    image = Image.open(io.BytesIO(image_bytes))
    image = ImageOps.exif_transpose(image)
    image = image.convert("RGB")

    width, height = image.size
    max_dim = 1200
    if width > max_dim or height > max_dim:
        image.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
        width, height = image.size

    draw = ImageDraw.Draw(image)
    top_text, bottom_text = parse_meme_text(caption)
    
    horiz_margin = int(width * 0.05)
    vert_margin = int(height * 0.04)
    max_text_width = width - (horiz_margin * 2)
    max_section_height = int(height * 0.40)
    initial_font_size = max(24, int(height * 0.10))

    if top_text:
        font_top, lines_top, size_top = get_optimal_font_and_lines(
            draw=draw,
            text=top_text,
            max_width=max_text_width,
            max_height=max_section_height,
            font_path=font_path,
            initial_font_size=initial_font_size
        )
        draw_text_with_outline(
            draw=draw,
            lines=lines_top,
            font=font_top,
            font_size=size_top,
            image_width=width,
            y_start=vert_margin
        )

    if bottom_text:
        font_bottom, lines_bottom, size_bottom = get_optimal_font_and_lines(
            draw=draw,
            text=bottom_text,
            max_width=max_text_width,
            max_height=max_section_height,
            font_path=font_path,
            initial_font_size=initial_font_size
        )
        
        line_spacing = int(size_bottom * 0.15)
        total_bottom_height = 0
        for line in lines_bottom:
            bbox = draw.textbbox((0, 0), line, font=font_bottom)
            total_bottom_height += (bbox[3] - bbox[1]) + line_spacing
        
        y_start_bottom = height - vert_margin - total_bottom_height
        if top_text and y_start_bottom < vert_margin + 50:
            y_start_bottom = vert_margin + 50

        draw_text_with_outline(
            draw=draw,
            lines=lines_bottom,
            font=font_bottom,
            font_size=size_bottom,
            image_width=width,
            y_start=y_start_bottom
        )

    output_io = io.BytesIO()
    image.save(output_io, format="JPEG", quality=90)
    return output_io.getvalue()


# -------------------------------------------------------------
# 2. КЛАССИЧЕСКИЙ ДЕМОТИВАТОР (.дем)
# -------------------------------------------------------------
def generate_demotivator(image_bytes: bytes, text: str) -> bytes:
    image = Image.open(io.BytesIO(image_bytes))
    image = ImageOps.exif_transpose(image)
    image = image.convert("RGB")

    img_w, img_h = image.size
    target_img_w = 700
    target_img_h = int(img_h * (target_img_w / img_w))
    image = image.resize((target_img_w, target_img_h), Image.Resampling.LANCZOS)

    pad_horiz = 70
    pad_top = 50
    text_area_h = 160
    
    canvas_w = target_img_w + (pad_horiz * 2)
    canvas_h = target_img_h + pad_top + text_area_h

    canvas = Image.new("RGB", (canvas_w, canvas_h), color=(0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    img_x = pad_horiz
    img_y = pad_top
    canvas.paste(image, (img_x, img_y))

    border_gap = 5
    draw.rectangle(
        [
            (img_x - border_gap, img_y - border_gap),
            (img_x + target_img_w + border_gap, img_y + target_img_h + border_gap)
        ],
        outline=(255, 255, 255),
        width=2
    )

    title_text = text.strip()
    subtitle_text = ""
    for sep in [";", "\n", "|"]:
        if sep in text:
            parts = text.split(sep, 1)
            title_text = parts[0].strip()
            subtitle_text = parts[1].strip()
            break

    font_file = str(TIMES_FONT_PATH) if TIMES_FONT_PATH.exists() else str(FONT_PATH)

    title_size = 46
    try:
        title_font = ImageFont.truetype(font_file, title_size)
    except Exception:
        title_font = ImageFont.load_default()

    bbox_t = draw.textbbox((0, 0), title_text, font=title_font)
    title_w = bbox_t[2] - bbox_t[0]
    title_x = (canvas_w - title_w) // 2
    title_y = img_y + target_img_h + border_gap + 20
    draw.text((title_x, title_y), title_text, font=title_font, fill=(255, 255, 255))

    if subtitle_text:
        sub_size = 24
        try:
            sub_font = ImageFont.truetype(font_file, sub_size)
        except Exception:
            sub_font = ImageFont.load_default()

        bbox_s = draw.textbbox((0, 0), subtitle_text, font=sub_font)
        sub_w = bbox_s[2] - bbox_s[0]
        sub_x = (canvas_w - sub_w) // 2
        sub_y = title_y + (bbox_t[3] - bbox_t[1]) + 12
        draw.text((sub_x, sub_y), subtitle_text, font=sub_font, fill=(255, 255, 255))

    output_io = io.BytesIO()
    canvas.save(output_io, format="JPEG", quality=90)
    return output_io.getvalue()


# -------------------------------------------------------------
# 3. ШАКАЛИЗАТОР / ПРОЖАРКА (.шакал / .дипфрай)
# -------------------------------------------------------------
def generate_deepfry(image_bytes: bytes) -> bytes:
    image = Image.open(io.BytesIO(image_bytes))
    image = ImageOps.exif_transpose(image)
    image = image.convert("RGB")

    image = ImageEnhance.Color(image).enhance(2.8)
    image = ImageEnhance.Contrast(image).enhance(2.2)
    image = ImageEnhance.Sharpness(image).enhance(4.0)
    image = image.filter(ImageFilter.EDGE_ENHANCE_MORE)

    buf1 = io.BytesIO()
    image.save(buf1, format="JPEG", quality=15)
    
    img2 = Image.open(io.BytesIO(buf1.getvalue()))
    img2 = ImageEnhance.Contrast(img2).enhance(1.8)
    img2 = ImageEnhance.Color(img2).enhance(1.5)

    output_io = io.BytesIO()
    img2.save(output_io, format="JPEG", quality=8)
    return output_io.getvalue()


# -------------------------------------------------------------
# 4. СПИЧ-БАБЛ / SPEECH BUBBLE (.бабл)
# -------------------------------------------------------------
def generate_speech_bubble(image_bytes: bytes) -> bytes:
    image = Image.open(io.BytesIO(image_bytes))
    image = ImageOps.exif_transpose(image)
    image = image.convert("RGBA")
    
    w, h = image.size
    bubble_h = int(h * 0.18)

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    draw.ellipse(
        [(-int(w * 0.1), -bubble_h), (int(w * 1.1), bubble_h)],
        fill=(255, 255, 255, 255)
    )
    tail_x = int(w * 0.35)
    draw.polygon(
        [(tail_x, bubble_h - 10), (tail_x + 35, bubble_h - 10), (tail_x + 10, bubble_h + int(h * 0.08))],
        fill=(255, 255, 255, 255)
    )

    combined = Image.alpha_composite(image, overlay).convert("RGB")
    output_io = io.BytesIO()
    combined.save(output_io, format="JPEG", quality=90)
    return output_io.getvalue()


# -------------------------------------------------------------
# 5. СИММЕТРИЯ ЛИЦА / МИРРОР (.лево / .право)
# -------------------------------------------------------------
def generate_symmetry(image_bytes: bytes, side: str = "left") -> bytes:
    """Mirrors the left or right half of the picture to create funny alien symmetrical faces."""
    image = Image.open(io.BytesIO(image_bytes))
    image = ImageOps.exif_transpose(image)
    image = image.convert("RGB")
    
    w, h = image.size
    half_w = w // 2

    if side == "left":
        left_half = image.crop((0, 0, half_w, h))
        flipped_left = ImageOps.mirror(left_half)
        res = Image.new("RGB", (w, h))
        res.paste(left_half, (0, 0))
        res.paste(flipped_left, (half_w, 0))
    else:
        right_half = image.crop((half_w, 0, w, h))
        flipped_right = ImageOps.mirror(right_half)
        res = Image.new("RGB", (w, h))
        res.paste(flipped_right, (0, 0))
        res.paste(right_half, (half_w, 0))

    output_io = io.BytesIO()
    res.save(output_io, format="JPEG", quality=92)
    return output_io.getvalue()


# -------------------------------------------------------------
# 6. ВОЛЧЬЯ ПАЦАНСКАЯ ЦИТАТА / СТЭТХЕМ (.волк / .цитата)
# -------------------------------------------------------------
def generate_wolf_quote(image_bytes: bytes, text: str) -> bytes:
    """Black and white atmospheric quote with dark vignette and signature."""
    image = Image.open(io.BytesIO(image_bytes))
    image = ImageOps.exif_transpose(image)
    
    # Convert to black and white with high drama
    image = ImageOps.grayscale(image).convert("RGB")
    image = ImageEnhance.Contrast(image).enhance(1.4)
    image = ImageEnhance.Brightness(image).enhance(0.75)

    w, h = image.size
    draw = ImageDraw.Draw(image)

    # Split quote and author (default: © Джейсон Стэтхем / © Ауф)
    quote_body = text.strip()
    author = "© Джейсон Стэтхем"
    for sep in [";", "\n", "|"]:
        if sep in text:
            parts = text.split(sep, 1)
            quote_body = parts[0].strip()
            author = f"© {parts[1].strip()}"
            break

    quote_formatted = f"«{quote_body}»"

    font_file = str(TIMES_FONT_PATH) if TIMES_FONT_PATH.exists() else str(FONT_PATH)
    font_size = max(24, int(h * 0.065))
    try:
        font = ImageFont.truetype(font_file, font_size)
        author_font = ImageFont.truetype(font_file, int(font_size * 0.65))
    except Exception:
        font = ImageFont.load_default()
        author_font = font

    # Wrap quote lines
    chars_per_line = max(10, int(w / (font_size * 0.45)))
    lines = textwrap.wrap(quote_formatted, width=chars_per_line)
    
    total_text_h = len(lines) * int(font_size * 1.3) + int(font_size * 1.2)
    y_start = h - int(h * 0.1) - total_text_h

    # Draw semi-transparent dark gradient bar at bottom for readability
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        lw = bbox[2] - bbox[0]
        lx = (w - lw) // 2
        ly = y_start + (i * int(font_size * 1.3))
        # Draw with slight shadow
        draw.text((lx + 2, ly + 2), line, font=font, fill=(0, 0, 0))
        draw.text((lx, ly), line, font=font, fill=(255, 255, 255))

    # Draw author
    bbox_a = draw.textbbox((0, 0), author, font=author_font)
    aw = bbox_a[2] - bbox_a[0]
    ax = (w - aw) // 2
    ay = y_start + (len(lines) * int(font_size * 1.3)) + 10
    draw.text((ax + 2, ay + 2), author, font=author_font, fill=(0, 0, 0))
    draw.text((ax, ay), author, font=author_font, fill=(220, 220, 220))

    output_io = io.BytesIO()
    image.save(output_io, format="JPEG", quality=90)
    return output_io.getvalue()


# -------------------------------------------------------------
# 7. ТРАУР / RIP (.рип / .память)
# -------------------------------------------------------------
def generate_rip(image_bytes: bytes) -> bytes:
    """Black-and-white mourning portrait with black ribbon in the corner and candle/text."""
    image = Image.open(io.BytesIO(image_bytes))
    image = ImageOps.exif_transpose(image)
    image = ImageOps.grayscale(image).convert("RGB")
    
    w, h = image.size
    draw = ImageDraw.Draw(image)

    # Black mourning ribbon in bottom-right corner
    ribbon_size = int(min(w, h) * 0.35)
    draw.polygon(
        [(w, h - ribbon_size), (w, h), (w - ribbon_size, h)],
        fill=(15, 15, 15)
    )

    # Text at the bottom left
    font_file = str(TIMES_FONT_PATH) if TIMES_FONT_PATH.exists() else str(FONT_PATH)
    font_size = max(20, int(h * 0.05))
    try:
        font = ImageFont.truetype(font_file, font_size)
    except Exception:
        font = ImageFont.load_default()

    text = "Помним... Любим... Скорбим..."
    draw.text((int(w * 0.05) + 2, h - int(h * 0.08) + 2), text, font=font, fill=(0, 0, 0))
    draw.text((int(w * 0.05), h - int(h * 0.08)), text, font=font, fill=(255, 255, 255))

    output_io = io.BytesIO()
    image.save(output_io, format="JPEG", quality=90)
    return output_io.getvalue()


# -------------------------------------------------------------
# 8. СРОЧНЫЕ НОВОСТИ / BREAKING NEWS (.новости / .news)
# -------------------------------------------------------------
def generate_breaking_news(image_bytes: bytes, text: str) -> bytes:
    """Adds a realistic TV breaking news banner at the bottom."""
    image = Image.open(io.BytesIO(image_bytes))
    image = ImageOps.exif_transpose(image)
    image = image.convert("RGB")

    w, h = image.size
    draw = ImageDraw.Draw(image)

    banner_h = int(h * 0.18)
    top_bar_h = int(banner_h * 0.38)
    y_banner = h - banner_h

    # Top red bar ("СРОЧНЫЕ НОВОСТИ")
    draw.rectangle([(0, y_banner), (w, y_banner + top_bar_h)], fill=(200, 20, 20))
    
    # Bottom dark blue bar for ticker headline
    draw.rectangle([(0, y_banner + top_bar_h), (w, h)], fill=(25, 30, 45))

    font_file = str(FONT_PATH)
    try:
        header_font = ImageFont.truetype(font_file, max(16, int(top_bar_h * 0.75)))
        ticker_font = ImageFont.truetype(font_file, max(18, int((banner_h - top_bar_h) * 0.65)))
    except Exception:
        header_font = ImageFont.load_default()
        ticker_font = ImageFont.load_default()

    # Draw Header "СРОЧНЫЕ НОВОСТИ" / "BREAKING NEWS"
    draw.text((int(w * 0.04), y_banner + 3), "● СРОЧНЫЕ НОВОСТИ", font=header_font, fill=(255, 255, 255))

    # Draw user headline
    headline = text.upper() if text else "ШОКИРУЮЩИЕ ПОДРОБНОСТИ В ЭФИРЕ"
    draw.text((int(w * 0.04), y_banner + top_bar_h + 8), headline, font=ticker_font, fill=(255, 255, 100))

    output_io = io.BytesIO()
    image.save(output_io, format="JPEG", quality=90)
    return output_io.getvalue()
