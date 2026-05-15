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
    """Generate 3 visuals only: two clean product angles + one full lifestyle/worn image.
    The original user photo is not used in the final poster; it is only a reference.
    """
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    ref = _prep_reference(source_image, out_dir)
    fallback = [ref, ref, ref]
    if not settings.enable_ai_image_gen or not settings.openai_api_key:
        return fallback

    name = product.get("name", "product")
    color = product.get("color", "same color")
    category = product.get("category", "product")
    is_shoe = "oyoq" in category.lower() or "kross" in name.lower() or "shoe" in name.lower() or "poyabzal" in category.lower()
    is_cloth = "kiyim" in category.lower() or "ko'yl" in name.lower() or "ko‘yl" in name.lower() or "futbolka" in name.lower()

    base_rules = (
        "Use the uploaded reference product only as the source of truth. "
        "Preserve product type, black color if black, knitted/mesh texture, sole shape, visible stripes and logo position as much as possible. "
        "Do not add text, watermark, price, brand label, extra objects, duplicate products, or changed colors. "
        "Make it photorealistic e-commerce advertising quality."
    )

    prompts = [
        f"{base_rules} Create a clean studio marketplace render of the same {name}, front three-quarter view, product fully visible, centered, premium light background.",
        f"{base_rules} Create a clean studio marketplace render of the same {name}, opposite side/back three-quarter view, product fully visible, centered, premium light background.",
    ]
    if is_shoe:
        prompts.append(
            f"{base_rules} Create a lifestyle image where a person is wearing the same {name} on foot. Show the full shoe and enough of the foot/ankle clearly, not cropped. Neutral pants, clean floor/studio setting, realistic scale."
        )
    elif is_cloth:
        prompts.append(
            f"{base_rules} Create a lifestyle fashion image of a model wearing the exact same clothing item. Show the full clothing item clearly, not cropped, clean e-commerce setting."
        )
    else:
        prompts.append(
            f"{base_rules} Create a lifestyle advertising image of the exact same product being used naturally. Product fully visible and clear, premium clean setting."
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
    except Exception:
        return fallback
