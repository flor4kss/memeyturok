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
    """Creates a classic 2000s demotivator with black frame, white border, and serif text."""
    image = Image.open(io.BytesIO(image_bytes))
    image = ImageOps.exif_transpose(image)
    image = image.convert("RGB")

    # Resize input image to standard size
    img_w, img_h = image.size
    target_img_w = 700
    target_img_h = int(img_h * (target_img_w / img_w))
    image = image.resize((target_img_w, target_img_h), Image.Resampling.LANCZOS)

    # Frame calculations
    pad_horiz = 70
    pad_top = 50
    text_area_h = 160
    
    canvas_w = target_img_w + (pad_horiz * 2)
    canvas_h = target_img_h + pad_top + text_area_h

    # Black canvas
    canvas = Image.new("RGB", (canvas_w, canvas_h), color=(0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    # Paste image
    img_x = pad_horiz
    img_y = pad_top
    canvas.paste(image, (img_x, img_y))

    # Outer white/grey border around image
    border_gap = 5
    draw.rectangle(
        [
            (img_x - border_gap, img_y - border_gap),
            (img_x + target_img_w + border_gap, img_y + target_img_h + border_gap)
        ],
        outline=(255, 255, 255),
        width=2
    )

    # Split text into Title and Subtitle
    title_text = text.strip()
    subtitle_text = ""
    for sep in [";", "\n", "|"]:
        if sep in text:
            parts = text.split(sep, 1)
            title_text = parts[0].strip()
            subtitle_text = parts[1].strip()
            break

    font_file = str(TIMES_FONT_PATH) if TIMES_FONT_PATH.exists() else str(FONT_PATH)

    # Draw Title (Large serif)
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

    # Draw Subtitle (Medium font)
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
    """Overheats contrast, saturation, sharpness and compresses down to 5% JPEG for extreme shitpost vibes."""
    image = Image.open(io.BytesIO(image_bytes))
    image = ImageOps.exif_transpose(image)
    image = image.convert("RGB")

    # Boost color saturation
    image = ImageEnhance.Color(image).enhance(2.8)
    # Boost contrast
    image = ImageEnhance.Contrast(image).enhance(2.2)
    # Boost sharpness
    image = ImageEnhance.Sharpness(image).enhance(4.0)
    # Edge enhance
    image = image.filter(ImageFilter.EDGE_ENHANCE_MORE)

    # First rough compression
    buf1 = io.BytesIO()
    image.save(buf1, format="JPEG", quality=15)
    
    # Reload and blast contrast one more time
    img2 = Image.open(io.BytesIO(buf1.getvalue()))
    img2 = ImageEnhance.Contrast(img2).enhance(1.8)
    img2 = ImageEnhance.Color(img2).enhance(1.5)

    # Final ultra-low-quality save
    output_io = io.BytesIO()
    img2.save(output_io, format="JPEG", quality=8)
    return output_io.getvalue()


# -------------------------------------------------------------
# 4. СПИЧ-БАБЛ / SPEECH BUBBLE (.бабл)
# -------------------------------------------------------------
def generate_speech_bubble(image_bytes: bytes) -> bytes:
    """Adds a transparent speech bubble tail cutout at the top of the image."""
    image = Image.open(io.BytesIO(image_bytes))
    image = ImageOps.exif_transpose(image)
    image = image.convert("RGBA")
    
    w, h = image.size
    bubble_h = int(h * 0.18)

    # Draw oval speech bubble with white fill on top
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Bubble oval
    draw.ellipse(
        [(-int(w * 0.1), -bubble_h), (int(w * 1.1), bubble_h)],
        fill=(255, 255, 255, 255)
    )
    # Pointer tail pointing down
    tail_x = int(w * 0.35)
    draw.polygon(
        [(tail_x, bubble_h - 10), (tail_x + 35, bubble_h - 10), (tail_x + 10, bubble_h + int(h * 0.08))],
        fill=(255, 255, 255, 255)
    )

    combined = Image.alpha_composite(image, overlay).convert("RGB")

    output_io = io.BytesIO()
    combined.save(output_io, format="JPEG", quality=90)
    return output_io.getvalue()
