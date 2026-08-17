import io
import os
import textwrap
from pathlib import Path
from typing import Tuple, Optional, List
from PIL import Image, ImageDraw, ImageFont, ImageOps

BASE_DIR = Path(__file__).resolve().parent.parent
FONT_PATH = BASE_DIR / "assets" / "font.ttf"
TEMPLATES_DIR = BASE_DIR / "assets" / "templates"


def get_template_names() -> List[str]:
    """Returns list of available template identifiers."""
    if not TEMPLATES_DIR.exists():
        return []
    return [f.stem for f in TEMPLATES_DIR.glob("*.jpg")]


def get_template_bytes(template_name: str) -> Optional[bytes]:
    """Reads raw bytes of a template image."""
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
    """
    Finds the best font size and wrapped lines to fit within max_width and max_height.
    """
    font_size = initial_font_size
    
    while font_size >= min_font_size:
        try:
            font = ImageFont.truetype(font_path, font_size)
        except Exception:
            font = ImageFont.load_default()
            return font, [text], 10

        # Estimate average character width for textwrap
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

        # Calculate total bounding box
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

    # Fallback to minimum font
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
    """
    Draws multiline centered text with a thick black outline.
    """
    stroke_width = max(2, int(font_size * stroke_ratio))
    line_spacing = int(font_size * 0.15)
    current_y = y_start

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        
        # Center horizontally
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
    """
    Parses user text into (top_text, bottom_text).
    Supports separators: ';', '\\n', '|'.
    If no separator is present, defaults to bottom text.
    """
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


def generate_meme(
    image_bytes: bytes,
    caption: str,
    font_path: Optional[str] = None
) -> bytes:
    """
    Takes input image bytes and caption text, overlays meme text with Impact font,
    and returns resulting JPEG bytes.
    """
    if font_path is None:
        font_path = str(FONT_PATH)

    image = Image.open(io.BytesIO(image_bytes))
    image = ImageOps.exif_transpose(image)
    image = image.convert("RGB")

    width, height = image.size

    # Limit max dimensions to keep rendering fast and lightweight
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
