from __future__ import annotations
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps, ImageEnhance
import textwrap, re


def _font(size: int, bold: bool = True):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for p in paths:
        try:
            return ImageFont.truetype(p, size=size)
        except Exception:
            pass
    return ImageFont.load_default()


def _safe(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", s.lower())[:45] or "product"


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


def _fit(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    im = ImageOps.exif_transpose(img.convert("RGB"))
    im.thumbnail(size, Image.LANCZOS)
    bg = Image.new("RGB", size, (245, 245, 245))
    bg.paste(im, ((size[0]-im.width)//2, (size[1]-im.height)//2))
    return bg


def _round_paste(canvas: Image.Image, img: Image.Image, box: tuple[int, int, int, int], radius: int = 32):
    x1, y1, x2, y2 = box
    tile = _cover(img, (x2-x1, y2-y1))
    mask = Image.new("L", tile.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, tile.width, tile.height], radius=radius, fill=255)
    shadow = Image.new("RGBA", (tile.width+50, tile.height+50), (0,0,0,0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle([25,25,tile.width+25,tile.height+25], radius=radius, fill=(0,0,0,90))
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))
    canvas.paste(shadow.convert("RGB"), (x1-25, y1-20), shadow)
    canvas.paste(tile, (x1, y1), mask)


def _draw_wrap(draw, xy, text, font, fill, max_width_px, max_lines=2, gap=8):
    words = (text or "").split()
    lines, cur = [], ""
    for word in words:
        test = (cur + " " + word).strip()
        if draw.textbbox((0,0), test, font=font)[2] <= max_width_px:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    y = xy[1]
    for line in lines[:max_lines]:
        draw.text((xy[0], y), line, font=font, fill=fill)
        y += font.size + gap
    return y


def make_final_poster(source_image: str, generated_images: list[str], product: dict, out_dir: str) -> str:
    """One final ad image: original + generated angles/lifestyle + short post inside same poster."""
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    original = Image.open(source_image).convert("RGB")
    visuals = [Image.open(p).convert("RGB") for p in generated_images[:3] if Path(p).exists()]
    while len(visuals) < 3:
        visuals.append(original)

    W, H = 1080, 1350
    bg = _cover(original, (W, H)).filter(ImageFilter.GaussianBlur(28))
    bg = ImageEnhance.Brightness(bg).enhance(0.65)
    canvas = bg.copy()
    draw = ImageDraw.Draw(canvas)

    # top header
    draw.rounded_rectangle([44, 42, W-44, 132], radius=36, fill=(255,255,255))
    draw.text((74, 64), "YANGI MAHSULOT", font=_font(34), fill=(20,20,20))

    # main visual grid
    _round_paste(canvas, original, (54, 165, 600, 735), 36)
    _round_paste(canvas, visuals[0], (630, 165, 1026, 430), 30)
    _round_paste(canvas, visuals[1], (630, 460, 1026, 735), 30)
    _round_paste(canvas, visuals[2], (54, 765, 1026, 1042), 36)

    # bottom post block
    draw.rounded_rectangle([44, 1070, W-44, H-42], radius=40, fill=(255,255,255))
    title = product.get("poster_title") or product.get("name") or "Yangi mahsulot"
    subtitle = product.get("poster_subtitle") or product.get("description") or "Buyurtma uchun yozing"
    caption = product.get("caption") or "Buyurtma uchun Telegram orqali yozing."
    features = product.get("short_features") or []

    y = 1102
    y = _draw_wrap(draw, (78, y), title, _font(50), (0,0,0), W-150, max_lines=2, gap=10)
    short = subtitle
    if features:
        short = " • ".join([str(x) for x in features[:3]])
    y += 8
    y = _draw_wrap(draw, (78, y), short, _font(28, False), (55,55,55), W-150, max_lines=2, gap=8)
    y += 6
    # very short sale line, not too much info
    clean_caption = " ".join(caption.replace("\n", " ").split())
    y = _draw_wrap(draw, (78, y), clean_caption, _font(24, False), (70,70,70), W-150, max_lines=2, gap=7)

    out = str(Path(out_dir) / f"final_poster_{_safe(title)}.jpg")
    canvas.save(out, quality=95)
    return out
