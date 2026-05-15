from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import textwrap


def _font(size: int):
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
        try: return ImageFont.truetype(p, size=size)
        except Exception: pass
    return ImageFont.load_default()


def make_ad_cards(frame_path: str, title: str, category: str, out_dir: str) -> list[str]:
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    base = Image.open(frame_path).convert("RGB")
    outputs = []
    formats = [(1080,1080,"post"), (1080,1920,"story"), (1280,720,"wide")]
    for w,h,name in formats:
        bg = base.copy(); bg.thumbnail((w,h))
        canvas = Image.new("RGB", (w,h), (245,245,245))
        blurred = base.resize((w,h)).filter(ImageFilter.GaussianBlur(14))
        canvas.paste(blurred, (0,0))
        x=(w-bg.width)//2; y=(h-bg.height)//2
        canvas.paste(bg,(x,y))
        draw=ImageDraw.Draw(canvas)
        bar_h = 170 if h <= 1080 else 230
        draw.rectangle([0,h-bar_h,w,h], fill=(255,255,255))
        draw.text((40,h-bar_h+25), "🔥 YANGI MAHSULOT", font=_font(36), fill=(20,20,20))
        for i,line in enumerate(textwrap.wrap(title, width=26)[:2]):
            draw.text((40,h-bar_h+75+i*42), line, font=_font(34), fill=(0,0,0))
        draw.text((40,h-45), f"#{category.replace('_',' ')}  |  Telegram orqali buyurtma", font=_font(24), fill=(70,70,70))
        out=str(Path(out_dir)/f"{name}.jpg")
        canvas.save(out, quality=92)
        outputs.append(out)
    return outputs
