from pathlib import Path
import cv2
from PIL import Image


def extract_frames(video_path: str, out_dir: str, count: int = 10) -> list[str]:
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(video_path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if total <= 0:
        cap.release(); return []
    indexes = sorted(set(int(i * total / (count + 1)) for i in range(1, count + 1)))
    frames = []
    for idx in indexes:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, frame = cap.read()
        if not ok: continue
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)
        img.thumbnail((1280, 1280))
        p = str(Path(out_dir) / f"frame_{idx}.jpg")
        img.save(p, quality=88)
        frames.append(p)
    cap.release()
    return frames
