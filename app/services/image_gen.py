from __future__ import annotations

from pathlib import Path
import base64
from PIL import Image, ImageOps, ImageEnhance
from openai import OpenAI
from app.config import settings


def _prep_reference(src_path: str, out_dir: str) -> str:
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    img = Image.open(src_path)
    img = ImageOps.exif_transpose(img).convert("RGB")
    img.thumbnail((1600, 1600), Image.LANCZOS)
    img = ImageEnhance.Sharpness(img).enhance(1.12)
    out = str(Path(out_dir) / "reference.png")
    img.save(out, "PNG")
    return out


def _save_b64(b64: str, path: str) -> str:
    Path(path).write_bytes(base64.b64decode(b64))
    return path


def generate_product_visuals(source_image: str, product: dict, out_dir: str) -> list[str]:
    """
    Generate 3 visuals:
    1) studio front/side product render
    2) studio opposite angle product render
    3) full lifestyle/worn image

    Original user photo is used only as reference, not placed in final poster.
    """
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    ref = _prep_reference(source_image, out_dir)
    fallback = [ref, ref, ref]

    if not settings.enable_ai_image_gen or not settings.openai_api_key:
        return fallback

    name = product.get("name", "product")
    color = product.get("color", "same color")
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

    base_rules = (
        "Use the uploaded reference product as the strict source of truth. "
        "Preserve the same product type, same color, same material texture, same sole shape if footwear, "
        "same knitted or mesh surface, same decorative stripes, same logo position and general silhouette. "
        "Do not invent a different model. Do not add text, watermark, price, label, box, extra accessories, "
        "extra logos, duplicate products, or changed colors. "
        "Photorealistic premium e-commerce advertising quality. "
    )

    prompts = [
        (
            f"{base_rules}"
            f"Create a clean studio product render of the same {name}. "
            f"Camera: front three-quarter view. "
            f"The entire product must be fully visible inside the frame with clear empty margins. "
            f"Do not crop any part of the product. Premium light background."
        ),
        (
            f"{base_rules}"
            f"Create a clean studio product render of the same {name}. "
            f"Camera: opposite side or back three-quarter view. "
            f"The entire product must be fully visible inside the frame with clear empty margins. "
            f"Do not crop toe, heel, sole, upper, logo, sleeve, collar, or edges. Premium light background."
        ),
    ]

    if is_shoe:
        prompts.append(
            f"{base_rules}"
            f"Create a lifestyle e-commerce photo where one person is wearing the same {name} on foot. "
            f"IMPORTANT: full shoe must be visible from toe to heel. "
            f"No part of the shoe may be cropped or cut off. "
            f"Show the entire shoe, complete sole, full toe, full heel, ankle opening, side logo and decorative stripes. "
            f"Use zoomed-out camera framing with enough empty margin around the shoe. "
            f"Show lower leg and ankle only, neutral pants, clean floor or studio background. "
            f"Realistic scale, professional marketplace photo, no text."
        )
    elif is_cloth:
        prompts.append(
            f"{base_rules}"
            f"Create a lifestyle fashion e-commerce photo of a model wearing the exact same clothing item. "
            f"IMPORTANT: show the full clothing item clearly from top to bottom. "
            f"No part of the clothing item may be cropped or cut off. "
            f"Use zoomed-out framing with enough empty margin. Clean studio background, no text."
        )
    else:
        prompts.append(
            f"{base_rules}"
            f"Create a lifestyle advertising photo of the exact same product being used naturally. "
            f"IMPORTANT: the whole product must be fully visible, not cropped, with enough empty margin. "
            f"Premium clean setting, no text."
        )

    outputs = []

    try:
        client = OpenAI(api_key=settings.openai_api_key)

        for i, prompt in enumerate(prompts, 1):
            with open(ref, "rb") as img_file:
                result = client.images.edit(
                    model=settings.image_model,
                    image=img_file,
                    prompt=prompt,
                    size="1024x1024",
                )

            b64 = result.data[0].b64_json
            outputs.append(_save_b64(b64, str(Path(out_dir) / f"ai_visual_{i}.png")))

        return outputs

    except Exception as e:
        print(f"[image_gen] error: {e}")
        return fallback
