from pathlib import Path
import cv2
from PIL import Image, ImageOps, ImageFilter, ImageEnhance


def _sharpness(frame) -> float:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def extract_frames(video_path: str, out_dir: str, count: int = 12) -> list[str]:
    """Videodan eng sifatli kadrlarni oladi: blur kam, takror kam, reklama uchun yaroqli."""
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(video_path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if total <= 0:
        cap.release()
        return []

    sample_count = min(max(count * 4, 16), 60)
    indexes = sorted(set(int(i * total / (sample_count + 1)) for i in range(1, sample_count + 1)))
    candidates = []
    for idx in indexes:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, frame = cap.read()
        if not ok:
            continue
        score = _sharpness(frame)
        candidates.append((score, idx, frame))
    cap.release()

    candidates = sorted(candidates, key=lambda x: x[0], reverse=True)[:count]
    frames = []
    for score, idx, frame in sorted(candidates, key=lambda x: x[1]):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)
        img = ImageOps.exif_transpose(img)
        img.thumbnail((1440, 1440))
        # Yengil sifat oshirish, mahsulot rangini buzmasdan
        img = ImageEnhance.Sharpness(img).enhance(1.25)
        img = ImageEnhance.Contrast(img).enhance(1.05)
        p = str(Path(out_dir) / f"frame_{idx}.jpg")
        img.save(p, quality=92)
        frames.append(p)
    return frames


def prepare_image_frame(image_path: str, out_dir: str) -> list[str]:
    """Botga rasm yuborilganda uni video kadr kabi tayyorlaydi."""
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    img = Image.open(image_path).convert("RGB")
    img = ImageOps.exif_transpose(img)
    img.thumbnail((1440, 1440))
    img = ImageEnhance.Sharpness(img).enhance(1.2)
    img = ImageEnhance.Contrast(img).enhance(1.05)
    out = str(Path(out_dir) / "photo_source.jpg")
    img.save(out, quality=94)
    return [out]
