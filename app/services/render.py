from __future__ import annotations

from pathlib import Path
import re

from PIL import Image, ImageFilter, ImageOps, ImageEnhance, ImageDraw


def _safe(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", (s or "product").lower())[:45] or "product"


def _open_rgb(path: str) -> Image.Image:
    img = Image.open(path)
    img = ImageOps.exif_transpose(img)
    return img.convert("RGB")


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

    left = (nw - w) // 2
    top = (nh - h) // 2
    return im.crop((left, top, left + w, top + h))


def _fit_on_blur(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    """
    Rasmni oq joysiz sig‘diradi.
    Orqa fon sifatida o‘sha rasmning blur qilingan varianti ishlatiladi.
    """
    w, h = size
    src = ImageOps.exif_transpose(img.convert("RGB"))

    bg = _cover(src, size)
    bg = bg.filter(ImageFilter.GaussianBlur(26))
    bg = ImageEnhance.Brightness(bg).enhance(0.72)
    bg = ImageEnhance.Contrast(bg).enhance(0.95)

    fg = src.copy()
    fg.thumbnail((w - 36, h - 36), Image.LANCZOS)

    x = (w - fg.width) // 2
    y = (h - fg.height) // 2
    bg.paste(fg, (x, y))

    return bg


def _round_paste(
    canvas: Image.Image,
    img: Image.Image,
    box: tuple[int, int, int, int],
    radius: int = 34,
):
    x1, y1, x2, y2 = box
    size = (x2 - x1, y2 - y1)

    tile = _fit_on_blur(img, size)

    shadow = Image.new("RGBA", (size[0] + 60, size[1] + 60), (0, 0, 0, 0))
    d = ImageDraw.Draw(shadow)
    d.rounded_rectangle(
        [30, 30, size[0] + 30, size[1] + 30],
        radius=radius,
        fill=(0, 0, 0, 105),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(20))
    canvas.paste(shadow.convert("RGB"), (x1 - 30, y1 - 22), shadow)

    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, size[0], size[1]],
        radius=radius,
        fill=255,
    )

    canvas.paste(tile, (x1, y1), mask)


def _unique_existing_images(generated_images: list[str]) -> list[str]:
    """
    image_gen.py fallback holatda [ref, ref, ref] qaytaradi.
    Bu funksiya takrorlangan yo‘llarni olib tashlaydi.
    """
    result: list[str] = []
    seen: set[str] = set()

    for p in generated_images or []:
        if not p:
            continue

        path = Path(p)
        if not path.exists():
            continue

        key = str(path.resolve())
        if key in seen:
            continue

        seen.add(key)
        result.append(str(path))

    return result


def _make_single_poster(source_image: str, product: dict, out_dir: str) -> str:
    """
    AI rasm generatsiya ishlamasa ishlaydigan fallback poster.
    Bitta mahsulot rasmi 3 marta takrorlanmaydi.
    """
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    src = _open_rgb(source_image)

    W, H = 1080, 1350

    bg = _cover(src, (W, H))
    bg = bg.filter(ImageFilter.GaussianBlur(36))
    bg = ImageEnhance.Brightness(bg).enhance(0.55)
    bg = ImageEnhance.Contrast(bg).enhance(0.95)

    canvas = bg.copy()

    margin = 58
    _round_paste(
        canvas,
        src,
        (margin, 90, W - margin, H - 90),
        radius=50,
    )

    title = product.get("name") or product.get("poster_title") or "product"
    out = str(Path(out_dir) / f"final_single_{_safe(title)}.jpg")
    canvas.save(out, quality=95, optimize=True)

    return out


def make_final_poster(
    source_image: str,
    generated_images: list[str],
    product: dict,
    out_dir: str,
) -> str:
    """
    Final poster.
    Rasm ichida matn yo‘q.
    Post matni Telegram caption sifatida alohida yuboriladi.
    """
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    unique_images = _unique_existing_images(generated_images)

    # Agar AI image_gen ishlamasa, [ref, ref, ref] keladi.
    # Bunday holatda 3 ta bir xil rasmli kollaj emas, bitta toza poster qilamiz.
    if len(unique_images) < 2:
        return _make_single_poster(source_image, product, out_dir)

    visuals = [_open_rgb(p) for p in unique_images[:3]]
    src = _open_rgb(source_image)

    while len(visuals) < 3:
        visuals.append(src)

    W, H = 1080, 1350

    bg = _cover(visuals[0], (W, H))
    bg = bg.filter(ImageFilter.GaussianBlur(34))
    bg = ImageEnhance.Brightness(bg).enhance(0.56)
    bg = ImageEnhance.Contrast(bg).enhance(0.95)

    canvas = bg.copy()

    margin = 50
    gap = 34

    top_y = 70
    top_h = 455
    col_w = (W - 2 * margin - gap) // 2

    _round_paste(
        canvas,
        visuals[0],
        (margin, top_y, margin + col_w, top_y + top_h),
        radius=38,
    )

    _round_paste(
        canvas,
        visuals[1],
        (margin + col_w + gap, top_y, W - margin, top_y + top_h),
        radius=38,
    )

    bottom_y = top_y + top_h + 44
    bottom_h = H - bottom_y - 70

    _round_paste(
        canvas,
        visuals[2],
        (margin, bottom_y, W - margin, bottom_y + bottom_h),
        radius=44,
    )

    title = product.get("name") or product.get("poster_title") or "product"
    out = str(Path(out_dir) / f"final_clean_collage_{_safe(title)}.jpg")
    canvas.save(out, quality=95, optimize=True)

    return out
