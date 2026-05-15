from __future__ import annotations
from pathlib import Path
import subprocess
import cv2
from PIL import Image, ImageOps, ImageEnhance


def _score_frame(frame) -> float:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    sharp = cv2.Laplacian(gray, cv2.CV_64F).var()
    bright = gray.mean()
    # too dark / too light frames are less useful
    light_penalty = abs(bright - 130) * 0.7
    return float(sharp - light_penalty)


def extract_frames(video_path: str, out_dir: str, count: int = 10) -> list[str]:
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(video_path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if total <= 0:
        cap.release()
        return []

    # take more candidates, then keep sharpest frames
    sample_count = min(max(count * 4, 16), 80)
    indexes = sorted(set(int(i * total / sample_count) for i in range(sample_count)))
    candidates: list[tuple[float, str]] = []

    for idx in indexes:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, frame = cap.read()
        if not ok or frame is None:
            continue
        score = _score_frame(frame)
        path = str(Path(out_dir) / f"frame_{idx}.jpg")
        cv2.imwrite(path, frame, [int(cv2.IMWRITE_JPEG_QUALITY), 94])
        candidates.append((score, path))
    cap.release()

    candidates.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in candidates[:count]]


def prepare_image_frame(image_path: str, out_dir: str) -> list[str]:
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    img = Image.open(image_path)
    img = ImageOps.exif_transpose(img).convert("RGB")
    img = ImageEnhance.Sharpness(img).enhance(1.15)
    img = ImageEnhance.Contrast(img).enhance(1.04)
    out = str(Path(out_dir) / "image_frame.jpg")
    img.save(out, quality=95)
    return [out]


def extract_audio(video_path: str, out_dir: str) -> str | None:
    """Extract audio from a video for transcription. Returns mp3 path or None."""
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    out = str(Path(out_dir) / "audio.mp3")
    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vn", "-ac", "1", "-ar", "16000", "-b:a", "64k", out
    ]
    try:
        p = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=35)
        if p.returncode == 0 and Path(out).exists() and Path(out).stat().st_size > 1000:
            return out
    except Exception:
        pass
    return None
