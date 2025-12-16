from PIL import Image, ImageDraw, ImageFont
from django.core.files.base import ContentFile
from django.conf import settings
from io import BytesIO
import os


def generate_design_preview(design):
    """
    Generates a PNG preview image for a Design instance
    """

    # ---- constants ----
    SCALE = 4
    WIDTH = 160 * SCALE
    HEIGHT = 113 * SCALE

    # ---- base image ----
    img = Image.new("RGB", (WIDTH, HEIGHT), "white")

    # ---- background ----
    if design.background_image and os.path.exists(design.background_image.path):
        bg = Image.open(design.background_image.path).convert("RGB")
        bg = bg.resize((WIDTH, HEIGHT))
        img.paste(bg, (0, 0))

    draw = ImageDraw.Draw(img)

    # ---- font ----
    font_path = os.path.join(
        settings.BASE_DIR,
        "design",
        "fonts",
        "Cairo-Bold.ttf"
    )

    try:
        font = ImageFont.truetype(
            font_path,
            max(10, design.serial_font_size * SCALE)
        )
    except OSError:
        font = ImageFont.load_default()

    # ---- draw serial ----
    x = design.serial_x * SCALE
    y = design.serial_y * SCALE

    draw.text(
        (x, y), 
        "12345678",
        fill=design.serial_color,
        font=font
    )

    # ---- output ----
    buffer = BytesIO()
    img.save(buffer, format="PNG", quality=95)

    return ContentFile(buffer.getvalue(), name="preview.png")
