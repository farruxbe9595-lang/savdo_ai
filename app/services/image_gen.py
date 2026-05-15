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
    img = ImageEnhance.Sharpness(img).enhance(1.10)
    out = str(Path(out_dir) / "reference.png")
    img.save(out, "PNG")
    return out


def _save_b64(b64: str, path: str) -> str:
    Path(path).write_bytes(base64.b64decode(b64))
    return path


def generate_product_visuals(source_image: str, product: dict, out_dir: str) -> list[str]:
    """Generate 3 marketing visuals from the original product image.
    Falls back to original image if image generation is unavailable.
    """
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    ref = _prep_reference(source_image, out_dir)
    fallback = [ref, ref, ref]
    if not settings.enable_ai_image_gen or not settings.openai_api_key:
        return fallback

    name = product.get("name", "product")
    color = product.get("color", "same color")
    category = product.get("category", "product")
    desc = product.get("description", "")
    is_shoe = "oyoq" in category.lower() or "kross" in name.lower() or "shoe" in name.lower()
    is_cloth = "kiyim" in category.lower() or "ko'yl" in name.lower() or "ko‘yl" in name.lower()

    prompts = [
        f"""Create a clean photorealistic marketplace product image using the reference product. Preserve the exact product identity, color, logo placement, sole/shape/details. Show the same {name} isolated on a premium light studio background, front three-quarter angle. No text, no watermark, no extra objects.""",
        f"""Create a second photorealistic marketplace view of the same reference {name}. Preserve exact design, color {color}, materials and all visible details. Show side/back angle on clean studio background. No text, no watermark.""",
    ]
    if is_shoe:
        prompts.append(f"""Create a realistic lifestyle image: a person wearing the exact same reference {name} on foot. Preserve the shoe color, knitted texture, sole shape and logo. Modern casual outfit, clean background. No text, no watermark, product must remain recognizable.""")
    elif is_cloth:
        prompts.append(f"""Create a realistic lifestyle fashion image: a model wearing the exact same reference clothing item. Preserve fabric, color, cut and visible design. Clean e-commerce style. No text, no watermark.""")
    else:
        prompts.append(f"""Create a realistic lifestyle advertising image of the exact same reference product being used naturally. Preserve product identity, color and details. Clean premium background. No text, no watermark.""")

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
    except Exception:
        return fallback
