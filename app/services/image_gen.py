from __future__ import annotations

from pathlib import Path
import time
import requests
from io import BytesIO
from urllib.parse import quote
from PIL import Image, ImageOps, ImageEnhance
from app.config import settings


def _prep_reference(src_path: str, out_dir: str) -> str:
    """Referens rasmni tayyorlash (agar fallback kerak bo'lsa)"""
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    img = Image.open(src_path)
    img = ImageOps.exif_transpose(img).convert("RGB")
    img.thumbnail((1600, 1600), Image.LANCZOS)
    img = ImageEnhance.Sharpness(img).enhance(1.12)
    out = str(Path(out_dir) / "reference.png")
    img.save(out, "PNG")
    return out


def _pollinations_generate(prompt: str, out_dir: str, retries: int = 3) -> str:
    """
    Pollinations.ai orqali FLUX rasm generatsiya qilish.
    BEPUL, API kalit kerakmas.
    15 soniyada 1 ta rasm limiti bor (anonymous tier).
    """
    import uuid

    # Promptni URL encoded qilish (uzunligi 1000 belgidan oshmasin)
    encoded = quote(prompt[:1000])

    url = f"https://image.pollinations.ai/prompt/{encoded}"

    params = {
        "model": "flux",
        "width": 1024,
        "height": 1024,
        "seed": str(uuid.uuid4().int)[:8],
        "nologo": "true",
    }

    last_error = None

    for attempt in range(retries):
        try:
            response = requests.get(url, params=params, timeout=90)

            if response.status_code == 429:
                # Rate limit — 15 soniya kutib, qayta urinish
                wait = 15
                print(f"[pollinations] rate limited, waiting {wait}s (attempt {attempt+1}/{retries})")
                time.sleep(wait)
                continue

            if response.status_code != 200:
                last_error = f"HTTP {response.status_code}: {response.text[:200]}"
                print(f"[pollinations] error: {last_error}")
                time.sleep(5)
                continue

            # Rasmni saqlash
            out_path = str(Path(out_dir) / f"pollinations_{uuid.uuid4().hex[:8]}.png")
            img = Image.open(BytesIO(response.content))
            img.save(out_path, quality=95)
            return out_path

        except requests.exceptions.Timeout:
            last_error = "timeout"
            print(f"[pollinations] timeout (attempt {attempt+1}/{retries})")
            time.sleep(10)
        except Exception as e:
            last_error = str(e)
            print(f"[pollinations] exception: {e}")
            time.sleep(5)

    raise RuntimeError(f"Pollinations failed after {retries} retries: {last_error}")


def generate_product_visuals(source_image: str, product: dict, out_dir: str) -> list[str]:
    """
    Generate 3 visuals using Pollinations.ai (free FLUX):
    1) studio front/side product render
    2) studio opposite angle product render
    3) full lifestyle/worn image

    Original user photo is used as reference for prompts.
    """
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    ref = _prep_reference(source_image, out_dir)

    # Agar rasm generatsiya o'chirilgan bo'lsa, referensni qaytarish
    if not settings.enable_ai_image_gen:
        return [ref, ref, ref]

    name = product.get("name", "product")
    color = product.get("color", "")
    category = product.get("category", "product")

    lower = f"{name} {category} {color}".lower()
    is_shoe = (
        "oyoq" in lower
        or "kross" in lower
        or "shoe" in lower
        or "poyabzal" in lower
        or "крос" in lower
        or "обув" in lower
    )
    is_cloth = (
        "kiyim" in lower
        or "ko'yl" in lower
        or "ko‘yl" in lower
        or "futbolka" in lower
        or "dress" in lower
        or "shirt" in lower
    )

    # Promptlar — Pollinations FLUX ingliz tilini yaxshi tushunadi
    prompts = [
        (
            f"Professional e-commerce studio product photo of {name} in {color}. "
            f"Front three-quarter view, entire product fully visible, clean white background, "
            f"photorealistic, premium quality, soft studio lighting, empty margins around product. "
            f"No text, no watermark, no logo."
        ),
        (
            f"Professional e-commerce studio product photo of {name} in {color}. "
            f"Back or opposite side three-quarter view, entire product fully visible, "
            f"clean white background, photorealistic, premium quality, soft studio lighting. "
            f"No text, no watermark, no logo."
        ),
    ]

    if is_shoe:
        prompts.append(
            f"Lifestyle e-commerce photo of a person wearing {name} in {color} on their feet. "
            f"Full shoe visible from toe to heel, no cropping, ankle and
            f"Full shoe visible from toe to heel, no cropping, ankle and lower leg visible, "
            f"neutral pants, clean studio floor background, professional marketplace photo. "
            f"No text, no watermark."
        )
    elif is_cloth:
        prompts.append(
            f"Lifestyle fashion e-commerce photo of a model wearing {name} in {color}. "
            f"Full clothing item visible from top to bottom, no cropping, "
            f"clean studio background, professional fashion photography. "
            f"No text, no watermark."
        )
    else:
        prompts.append(
            f"Lifestyle advertising photo of {name} in {color} being used naturally. "
            f"Whole product fully visible, not cropped, premium clean setting. "
            f"No text, no watermark."
        )

    outputs = []

    for i, prompt in enumerate(prompts, 1):
        try:
            print(f"[image_gen] generating visual {i}/3 via Pollinations...")
            path = _pollinations_generate(prompt, out_dir)
            outputs.append(path)
            # Rate limitni hurmat qilish — 15 soniya kutish
            if i < len(prompts):
                print(f"[image_gen] waiting 15s before next generation (rate limit)...")
                time.sleep(15)
        except Exception as e:
            print(f"[image_gen] visual {i} failed: {e}")
            outputs.append(ref)

    # Agar hammasi failed bo'lsa, referensni qaytarish
    if not outputs:
        return [ref, ref, ref]

    return outputs
