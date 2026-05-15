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
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", s.lower())[:40] or "product"


def _cover(img: Image.Image, size: tuple[int,int]) -> Image.Image:
    w, h = size
    im = img.copy().convert("RGB")
    im_ratio = im.width / im.height
    target_ratio = w / h
    if im_ratio > target_ratio:
        new_h = h
        new_w = int(h * im_ratio)
    else:
        new_w = w
        new_h = int(w / im_ratio)
    im = im.resize((new_w, new_h), Image.LANCZOS)
    x = (new_w - w) // 2
    y = (new_h - h) // 2
    return im.crop((x, y, x+w, y+h))


def _rounded_mask(size, radius):
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size[0], size[1]], radius=radius, fill=255)
    return mask


def _draw_wrapped(draw, xy, text, font, fill, width, line_gap=8, max_lines=3):
    x, y = xy
    lines = textwrap.wrap(text or "", width=width)[:max_lines]
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        y += font.size + line_gap
    return y


def _polish_product(src: Image.Image) -> Image.Image:
    img = ImageOps.exif_transpose(src.convert("RGB"))
    img = ImageEnhance.Sharpness(img).enhance(1.18)
    img = ImageEnhance.Contrast(img).enhance(1.06)
    img = ImageEnhance.Color(img).enhance(1.03)
    return img


def make_ad_cards(frame_path: str, title: str, category: str, out_dir: str, caption: str = "") -> list[str]:
    """Mahsulotning asl kadrini saqlagan holda 3 ta professional reklama format yaratadi."""
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    base = _polish_product(Image.open(frame_path))
    outputs = []
    specs = [
        (1080, 1080, "telegram_post"),
        (1080, 1920, "story"),
        (1280, 720, "wide_banner"),
    ]
    title = title or "Yangi mahsulot"
    category_text = (category or "mahsulot").replace("_", " ").title()

    for w, h, name in specs:
        # premium blurred background
        bg = _cover(base, (w, h)).filter(ImageFilter.GaussianBlur(24))
        bg = ImageEnhance.Brightness(bg).enhance(0.82)
        canvas = bg.copy()
        overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        od.rectangle([0, 0, w, h], fill=(0, 0, 0, 50))
        canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")

        draw = ImageDraw.Draw(canvas)
        margin = int(w * 0.055)
        if h > w:  # story
            product_box = (margin, 230, w - margin, int(h * 0.68))
            text_box_y = int(h * 0.70)
        elif w > h:  # wide
            product_box = (margin, 70, int(w * 0.56), h - 70)
            text_box_y = 95
        else:
            product_box = (margin, 130, w - margin, int(h * 0.72))
            text_box_y = int(h * 0.74)

        # product card
        x1, y1, x2, y2 = product_box
        pw, ph = x2-x1, y2-y1
        product = base.copy()
        product.thumbnail((pw, ph), Image.LANCZOS)
        px = x1 + (pw-product.width)//2
        py = y1 + (ph-product.height)//2
        shadow = Image.new("RGBA", (product.width+40, product.height+40), (0,0,0,0))
        sd = ImageDraw.Draw(shadow)
        sd.rounded_rectangle([20,20,product.width+20,product.height+20], radius=34, fill=(0,0,0,120))
        shadow = shadow.filter(ImageFilter.GaussianBlur(18))
        canvas.paste(shadow.convert("RGB"), (px-20, py-20), shadow)
        mask = _rounded_mask(product.size, 28)
        canvas.paste(product, (px, py), mask)

        # labels
        if w > h:
            tx = int(w * 0.61)
            ty = text_box_y
            draw.rounded_rectangle([tx-25, ty-35, w-margin, h-70], radius=34, fill=(255,255,255))
            draw.text((tx, ty), "YANGI MAHSULOT", font=_font(34), fill=(30,30,30))
            ty += 58
            ty = _draw_wrapped(draw, (tx, ty), title, _font(44), (0,0,0), 18, max_lines=3)
            ty += 15
            draw.text((tx, ty), category_text, font=_font(28, False), fill=(80,80,80))
            ty += 55
            _draw_wrapped(draw, (tx, ty), "Buyurtma uchun Telegram orqali yozing", _font(25, False), (40,40,40), 24, max_lines=2)
        else:
            panel_h = h - text_box_y
            draw.rounded_rectangle([0, text_box_y, w, h+40], radius=38, fill=(255,255,255))
            draw.text((margin, text_box_y+28), "🔥 YANGI MAHSULOT", font=_font(35), fill=(25,25,25))
            y = text_box_y + 82
            y = _draw_wrapped(draw, (margin, y), title, _font(42), (0,0,0), 24, max_lines=2)
            draw.text((margin, min(y+10, h-80)), f"#{(category or 'mahsulot').replace('_',' ')}  •  Telegram orqali buyurtma", font=_font(24, False), fill=(65,65,65))

        out = str(Path(out_dir) / f"{_safe(title)}_{name}.jpg")
        canvas.save(out, quality=94)
        outputs.append(out)
    return outputs
