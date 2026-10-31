"""Replay native Ruby draw calls with FreeType; never a game screenshot."""
import argparse
import json
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from fire_ash import ARTIFACTS, ROOT, digest, json_write


def save_preview(canvas, path):
    path = Path(path)
    assert path.resolve().is_relative_to(ARTIFACTS.resolve())
    if path.exists():
        with Image.open(path) as previous:
            if previous.mode == canvas.mode and previous.size == canvas.size and previous.tobytes() == canvas.tobytes():
                return
    # Windows rejects truncating an image held by a memory-mapped preview.
    part = path.with_name(path.name + ".preview-part")
    if part.exists():
        raise FileExistsError(f"Keep the failed preview evidence and inspect it first: {part}")
    canvas.save(part,format="PNG")
    os.replace(part,path)


def paint_scene(name, calls, font_path, expected_family, smooth, background=None):
    """Replay one native scene; return pixels and checks without writing reports."""
    dialogue = "dialogue" in name or name.startswith("smalltext")
    dark = name.startswith(("dark-", "smalltext"))
    battle = name.startswith("battle-")
    canvas = Image.new("RGB", (512, 384), (216, 232, 208) if dialogue else (248, 248, 248))
    draw = ImageDraw.Draw(canvas, "RGBA")
    if dialogue:
        fill = background or ((40,48,64) if dark else (248,248,248) if name.startswith(("blue-","red-")) else (248,248,240))
        draw.rectangle((16,288 if battle else 256,495,383 if battle else 375),fill=fill,outline=(56,72,80),width=4)
    else:
        draw.rectangle((8, 8, 503, 375), outline=(56,72,80), width=4)
        draw.line((16, 57, 495, 57), fill=(56,72,80), width=2)
    bounds, alpha_values, fonts = [], set(), {}
    for call in calls:
        x, y, width, height = call["rect"]
        if call["kind"] == "rect":
            assert 0 <= x < x+width <= 512 and 0 <= y < y+height <= 384
            draw.rectangle((x,y,x+width-1,y+height-1), fill=tuple(call["color"]))
            continue
        assert call["family"] == expected_family, call
        pixels = int(call["api_size"] * 0.9)
        if pixels not in fonts:
            fonts[pixels] = ImageFont.truetype(str(font_path), pixels, index=0, layout_engine=ImageFont.Layout.BASIC)
        font, value = fonts[pixels], call["text"]
        text_width = font.getlength(value)
        assert text_width <= width, ("Engine would squeeze text", name, value, text_width, width)
        assert text_width == int(text_width) and pixels % 12 == 0
        if call["align"] == 1:
            x += max(0, int((width-text_width)/2))
        elif call["align"] == 2:
            x += max(0, int(width-text_width))
        y += int((height-sum(font.getmetrics()))/2)
        box = draw.textbbox((x,y), value, font=font)
        assert 16 <= box[0] and box[2] <= 496 and 8 <= box[1] and box[3] <= 372, (name,value,box)
        if battle:
            assert 32 <= box[0] and box[2] <= 480 and 306 <= box[1] and box[3] <= 370, ("Battle contents clipping",value,box)
        alpha = set(bytes(font.getmask(value, mode="L")))
        alpha_values.update(alpha)
        if not smooth:
            assert alpha <= {0,255}
        draw.text((x,y), value, font=font, fill=tuple(call["color"]))
        bounds.append({"scene": name, "text": value, "box": box})
    if name == "settings-after":
        scale_row = [b for b in bounds if 280 <= b["box"][1] < 316]
        assert len(scale_row) == 6, ("Expected the label and all five scale choices", scale_row)
        assert [b["text"] for b in scale_row][1:] == ["S","M","L","XL","全螢幕"]
        boxes = sorted(b["box"] for b in scale_row)
        assert all(left[2] < right[0] for left,right in zip(boxes,boxes[1:])), ("Scale option collision", scale_row)
    return canvas, bounds, alpha_values


def main(args):
    output = ARTIFACTS / "images/fire-ash"
    output.mkdir(parents=True, exist_ok=True)
    coverage = json.loads((ROOT / "coverage.json").read_text(encoding="utf-8"))
    profile = coverage["font"].get("profile", "pixel")
    from fire_ash import staged_font_path
    font_path = args.font_sample.resolve() if args.font_sample else staged_font_path(profile)
    smooth = bool(args.font_sample) or profile in ("jhenghei","noto")
    work = (ARTIFACTS / "data/fire-ash-work/smooth-font-sample" if args.font_sample
            else ARTIFACTS / "data/fire-ash-work")
    recorded_path = work / "font-preview-draw-calls.json"
    recorded = json.loads(recorded_path.read_text(encoding="utf-8"))
    assert digest(font_path.read_bytes()) == recorded["font_sha256"]
    if args.font_sample:
        sample = json.loads((work / "validation.json").read_text(encoding="utf-8"))
        assert sample["passed"] and sample["sample_only"] and sample["font_sha256"] == recorded["font_sha256"]
        expected_family = sample["family"]
    else:
        assert recorded["font_sha256"] == coverage["font"]["sha256"]
        expected_family = coverage["font"]["family"]
    assert recorded["scripts_sha256"] == coverage["scripts_sha256"]
    samples = {}
    bounds = []
    alpha_values = set()

    for name, calls in recorded["scenes"].items():
        if args.font_sample and name.endswith("before"):
            continue
        canvas, scene_bounds, scene_alpha = paint_scene(name,calls,font_path,expected_family,smooth)
        bounds.extend(scene_bounds)
        alpha_values.update(scene_alpha)
        samples[name] = canvas

    previews = []
    for name, canvas in samples.items():
        suffix = ("smooth-sample" if args.font_sample else f"{profile}-trial" if profile in ("jhenghei","noto") and name.endswith("after") else
                  "no-shadow-only" if name.endswith("after") else "three-shadows-only")
        kind = name.rsplit("-",1)[0]
        for scale in (1,2,3.75,4):
            if scale == 3.75 and name.endswith("before"):
                continue
            path = output / f"font-preview-{kind}-{suffix}-{scale}x.png"
            save_preview(canvas.resize((int(512*scale),int(384*scale)),Image.Resampling.NEAREST),path)
            previews.append(str(path))
    for kind in ("settings","dialogue"):
        top = 8 if kind == "settings" else 256
        bottom = 376
        comparison = Image.new("RGB", (4096,(bottom-top)*4))
        if args.font_sample:
            baseline_suffix = f"{profile}-trial" if profile in ("jhenghei","noto") else "no-shadow-only"
            before = Image.open(output / f"font-preview-{kind}-{baseline_suffix}-1x.png").convert("RGB")
            assert before.size == (512,384)
        else:
            before = samples[f"{kind}-before"]
        for x, canvas in ((0,before),(2048,samples[f"{kind}-after"])):
            crop = canvas.crop((0,top,512,bottom))
            comparison.paste(crop.resize((2048,crop.height*4), Image.Resampling.NEAREST), (x,0))
        suffix = ("baseline-vs-smooth" if profile in ("jhenghei","noto") else "pixel-vs-smooth") if args.font_sample else (
            f"{profile}-trial" if profile in ("jhenghei","noto") else "no-shadow-only")
        path = output / f"font-preview-{kind}-{suffix}-comparison-4x.png"
        save_preview(comparison,path)
        previews.append(str(path))
    if profile == "jhenghei" and not args.font_sample:
        for kind in ("settings", "dialogue", "dark-dialogue", "smalltext"):
            top = 8 if kind == "settings" else 256
            canvas = samples[f"{kind}-after"].crop((0,top,512,376))
            path = output / f"font-preview-{kind}-jhenghei-trial-crop-3.75x.png"
            save_preview(canvas.resize((1920,int(canvas.height*3.75)),Image.Resampling.NEAREST),path)
            previews.append(str(path))
            baseline = Image.open(output / f"font-preview-{kind}-no-shadow-only-1x.png").convert("RGB")
            assert baseline.size == (512,384)
            comparison = Image.new("RGB", (3840,int(canvas.height*3.75)))
            comparison.paste(baseline.crop((0,top,512,376)).resize((1920,comparison.height),Image.Resampling.NEAREST),(0,0))
            comparison.paste(Image.open(path),(1920,0))
            path = output / f"font-preview-{kind}-pixel-vs-jhenghei-trial-3.75x.png"
            save_preview(comparison,path)
            previews.append(str(path))
    if profile == "noto":
        for kind in ("blue-dialogue","red-dialogue","settings","smalltext","battle-dialogue"):
            top = 8 if kind == "settings" else 288 if kind.startswith("battle-") else 256
            bottom = 384 if kind.startswith("battle-") else 376
            canvas = samples[f"{kind}-after"].crop((0,top,512,bottom))
            if args.font_sample:
                noto = Image.open(output / f"font-preview-{kind}-noto-trial-1x.png").convert("RGB")
                comparison = Image.new("RGB",(3840,int(canvas.height*3.75)))
                comparison.paste(canvas.resize((1920,comparison.height),Image.Resampling.NEAREST),(0,0))
                comparison.paste(noto.crop((0,top,512,bottom)).resize((1920,comparison.height),Image.Resampling.NEAREST),(1920,0))
                path = output / f"font-preview-{kind}-jhenghei-vs-noto-3.75x.png"
                save_preview(comparison,path)
            else:
                path = output / f"font-preview-{kind}-noto-trial-crop-3.75x.png"
                save_preview(canvas.resize((1920,int(canvas.height*3.75)),Image.Resampling.NEAREST),path)
            previews.append(str(path))
    report_path = work / "preview-validation.json" if args.font_sample else ROOT / "font-preview-validation.json"
    json_write(report_path, {
        "passed": True, "renderer": "Native Ruby call capture -> Pillow/FreeType grayscale; no threshold; not game screenshots",
        "sample_only": bool(args.font_sample), "family": expected_family, "font_profile": profile,
        "alpha_value_count": len(alpha_values),
        "canvas": [512,384], "scales": [1,2,3.75,4], "resampling": "NEAREST",
        "font_sha256": digest(font_path.read_bytes()), "language_sha256": coverage["language_sha256"],
        "scripts_sha256": coverage["scripts_sha256"], "draw_calls_sha256": digest(recorded_path.read_bytes()),
        "preview_tool_sha256": digest(Path(__file__).read_bytes()),
        "glyph_bounds_checked": len(bounds), "horizontal_squeeze_cases": 0,
        "fullscreen_choices_nonoverlapping": True, "fullscreen_choices_checked": 5,
        "battle_contents_checked": True,"vertical_offset_px": 0,
        "scene_call_counts": {name:len(calls) for name,calls in recorded["scenes"].items()},
        "bounds": bounds, "previews": previews, "game_started": False, "installed": False,
        "limitations": "已執行遊戲實際選單及文字函式，圖形API由記錄器替代；重播採FreeType。背景／游標為測試畫布，非SDL實機截圖；4x圖僅為檢查放大，不是新增遊戲顯示選項。"
    })
    print(f"PASS: {len(previews)} previews; {len(bounds)} text bounds; no horizontal squeeze; 1x/2x/3.75x/4x nearest-neighbor")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font-sample", type=Path, help="Replay an isolated 24px local-font sample, face index 0")
    main(parser.parse_args())
