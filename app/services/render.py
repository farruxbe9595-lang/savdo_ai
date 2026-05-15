from __future__ import annotations
from pathlib import Path
from PIL import Image, ImageFilter, ImageOps, ImageEnhance
import re


def _safe(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", (s or "product").lower())[:45] or "product"


def _cover(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    w, h = size
    im = ImageOps.exif_transpose(img.convert("RGB"))
    ratio = im.width / im.height
    target = w / h
    if ratio > target:
        nh = h
        nw = int(h * ratio)
    else:
        nw = w
        nh = int(w / ratio)
    im = im.resize((nw, nh), Image.LANCZOS)
    return im.crop(((nw-w)//2, (nh-h)//2, (nw+w)//2, (nh+h)//2))


def _fit(img: Image.Image, size: tuple[int, int], bg=(246, 246, 246)) -> Image.Image:
    im = ImageOps.exif_transpose(img.convert("RGB"))
    im.thumbnail(size, Image.LANCZOS)
    out = Image.new("RGB", size, bg)
    out.paste(im, ((size[0]-im.width)//2, (size[1]-im.height)//2))
    return out


def _round_paste(canvas: Image.Image, img: Image.Image, box: tuple[int, int, int, int], radius: int = 34, mode: str = "cover"):
    x1, y1, x2, y2 = box
    size = (x2-x1, y2-y1)
    tile = _cover(img, size) if mode == "cover" else _fit(img, size)

    # subtle shadow
    shadow = Image.new("RGBA", (size[0] + 48, size[1] + 48), (0, 0, 0, 0))
    sd = Image.new("L", size, 0)
    ImageOps.expand(sd, border=24, fill=0)
    from PIL import ImageDraw
    d = ImageDraw.Draw(shadow)
    d.rounded_rectangle([24, 24, size[0]+24, size[1]+24], radius=radius, fill=(0, 0, 0, 105))
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))
    canvas.paste(shadow.convert("RGB"), (x1-24, y1-18), shadow)

    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size[0], size[1]], radius=radius, fill=255)
    canvas.paste(tile, (x1, y1), mask)


def make_final_poster(source_image: str, generated_images: list[str], product: dict, out_dir: str) -> str:
    """Final poster without original user photo and without text.
    Layout: 2 product renders + 1 full lifestyle/worn image. Text is sent as Telegram caption outside image.
    """
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    src = Image.open(source_image).convert("RGB")
    visuals = [Image.open(p).convert("RGB") for p in generated_images[:3] if Path(p).exists()]
    while len(visuals) < 3:
        visuals.append(src)

    W, H = 1080, 1350
    bg = _cover(visuals[0] if visuals else src, (W, H)).filter(ImageFilter.GaussianBlur(32))
    bg = ImageEnhance.Brightness(bg).enhance(0.58)
    bg = ImageEnhance.Contrast(bg).enhance(0.95)
    canvas = bg.copy()

    # Product collage only. No title, no caption inside image.
    # Top: two clean product angles, bottom: big lifestyle/worn image, full object visible.
    margin = 50
    gap = 34
    top_y = 70
    top_h = 455
    col_w = (W - 2 * margin - gap) // 2

    _round_paste(canvas, visuals[0], (margin, top_y, margin + col_w, top_y + top_h), 38, mode="fit")
    _round_paste(canvas, visuals[1], (margin + col_w + gap, top_y, W - margin, top_y + top_h), 38, mode="fit")

    bottom_y = top_y + top_h + 44
    bottom_h = H - bottom_y - 70
    # Lifestyle image is fit, not cover, so full foot/product is visible.
    _round_paste(canvas, visuals[2], (margin, bottom_y, W - margin, bottom_y + bottom_h), 44, mode="fit")

    title = product.get("name") or product.get("poster_title") or "product"
    out = str(Path(out_dir) / f"final_clean_collage_{_safe(title)}.jpg")
    canvas.save(out, quality=95)
    return out
