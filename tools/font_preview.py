"""Render actual font masks on 512x384 samples, never a game screenshot."""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from fire_ash import ARTIFACTS, ROOT, digest, json_write, loads, text


def main():
    output = ARTIFACTS / "images/fire-ash"
    output.mkdir(parents=True, exist_ok=True)
    font_path = ARTIFACTS / "data/fire-ash-work/fonts/fire-ash-zhtw.ttf"
    coverage = json.loads((ROOT / "coverage.json").read_text(encoding="utf-8"))
    assert digest(font_path.read_bytes()) == coverage["font"]["sha256"]
    font = ImageFont.truetype(str(font_path), 24)
    old_font = ImageFont.truetype(r"C:\Windows\Fonts\msjh.ttc", 20, index=0)
    layout = json.loads((ARTIFACTS / "data/fire-ash-work/font-preview-layout.json").read_text(encoding="utf-8"))
    assert layout["font_sha256"] == coverage["font"]["sha256"]
    data = loads((ARTIFACTS / "release/fire-ash-zh-tw-preview/Data/traditional_chinese.dat").read_bytes())
    keys, values = loads(data[24]._dump())
    ui = {text(k): text(v) for k, v in zip(keys, values)}
    samples = []
    bounds = []

    def label(draw, xy, value, used_font, color=(48, 48, 48), right=480, bottom=376):
        x, y = xy
        box = draw.textbbox((x, y), value, font=used_font)
        assert box[0] >= 0 and box[2] + 2 <= right and box[3] + 2 <= bottom, (value, box, right, bottom)
        bounds.append({"text": value, "box": box, "right_limit": right, "bottom_limit": bottom})
        draw.text((x+2, y+2), value, font=used_font, fill=(184, 184, 176))
        draw.text((x, y), value, font=used_font, fill=color)

    def frame(dialogue=False):
        image = Image.new("RGB", (512, 384), (216, 232, 208) if dialogue else (248, 248, 232))
        draw = ImageDraw.Draw(image)
        if dialogue:
            draw.rectangle((16, 256, 495, 375), fill=(248, 248, 240), outline=(56, 72, 80), width=4)
        else:
            draw.rectangle((8, 8, 503, 375), outline=(56, 72, 80), width=4)
            draw.line((16, 57, 495, 57), fill=(56, 72, 80), width=2)
        return image, draw

    for old in (False, True):
        used = old_font if old else font
        suffix = "old" if old else "new"
        settings, draw = frame()
        label(draw, (32, 20), ui["Options"], used)
        rows = [("Music Volume", "100"), ("SE Volume", "80"), ("Text Speed", "Normal"),
                ("Battle Effects", "On"), ("Battle Style", "Switch"), ("Default Movement", "Walking"),
                ("Text Entry", "Keyboard"), ("Weather Effects", "On")]
        for i, (key, value) in enumerate(rows):
            y = 72 + i * 36
            label(draw, (32, y), ui[key], used, right=232)
            label(draw, (248, y), ui.get(value, value), used)
        samples.append((f"settings-{suffix}", settings))
        dialogue, draw = frame(True)
        # Keep the same formatter positions to isolate font rasterization.
        for cp, x, y, width, height in layout["rows"]:
            assert x + width - 2 <= 480 and y + height <= 368
            label(draw, (x, y), chr(cp), used, bottom=368)
        samples.append((f"dialogue-{suffix}", dialogue))

    previews = []
    for name, image in samples:
        native = output / f"font-preview-{name}-512.png"
        enlarged = output / f"font-preview-{name}-4x.png"
        image.save(native)
        image.resize((2048, 1536), Image.Resampling.NEAREST).save(enlarged)
        previews.extend([str(native), str(enlarged)])
    for kind in ("settings", "dialogue"):
        # One before/after comparison per image, as required for visual review.
        before = next(im for name, im in samples if name == f"{kind}-old")
        after = next(im for name, im in samples if name == f"{kind}-new")
        top = 8 if kind == "settings" else 256
        bottom = 376
        comparison = Image.new("RGB", (4096, (bottom-top)*4))
        for x, im in ((0, before), (2048, after)):
            crop = im.crop((0, top, 512, bottom))
            comparison.paste(crop.resize((2048, crop.height*4), Image.Resampling.NEAREST), (x, 0))
        path = output / f"font-preview-{kind}-comparison-4x.png"
        comparison.save(path)
        previews.append(str(path))
    json_write(ROOT / "font-preview-validation.json", {
        "passed": True, "renderer": "Pillow/FreeType grayscale; no threshold; not game screenshots",
        "canvas": [512, 384], "scale": 4, "resampling": "NEAREST",
        "font_sha256": digest(font_path.read_bytes()), "language_sha256": coverage["language_sha256"],
        "scripts_sha256": coverage["scripts_sha256"], "glyph_bounds_checked": len(bounds),
        "preview_tool_sha256": digest(Path(__file__).read_bytes()),
        "bounds": bounds, "dialogue_layout": layout["source"], "previews": previews,
        "game_started": False, "installed": False,
        "limitations": "預覽重現字型與排版尺寸，背景為測試用畫布；不是遊戲實機畫面，仍須Claude 1重新套用後驗收。"})
    print(f"PASS: {len(previews)} raster previews; {len(bounds)} text bounds; 512x384 -> 2048x1536 nearest-neighbor")


if __name__ == "__main__":
    main()
