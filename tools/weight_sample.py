"""Isolated A/B/C font-weight samples. Never builds, installs, or starts the game."""
import json
import re
import shutil
import sqlite3
import subprocess
import sys
import zlib
from pathlib import Path

from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont, features

import fire_ash as f
from font_preview import paint_scene, save_preview

WORK = f.ARTIFACTS / "data/fire-ash-work"
OUTPUT = f.ARTIFACTS / "images/fire-ash/weight-sample"
DATA = WORK / "weight-sample"
LOGS = f.ARTIFACTS / "logs/fire-ash-weight-sample"
BASELINE = WORK / "original-baseline"
FONTS = [
    ("a", "A Noto Medium 500", f.ARTIFACTS / "downloads/noto-sans-cjk-tc/NotoSansCJKtc-Medium.otf",
     "2905dd3de65d7b7de764596e2294978407986f4cc0a66c9584c5b95c5aa9572e", 500, "OFL-1.1"),
    ("b", "B JhengHei Bold 700", Path(r"C:\Windows\Fonts\msjhbd.ttc"),
     "7d55cd4801102131d991630cea74534dcf73a9fabf4a33e54fe05dfb4f5aa790", 700, "Microsoft; local only"),
    ("c", "C JhengHei Regular 400", Path(r"C:\Windows\Fonts\msjh.ttc"),
     "1fd5fc7046e0eea753988ee06d1a5a731df68475614e2174fbba9b4800f392ac", 400, "Microsoft; local only")
]


def target_characters():
    # Reuse the build's exact translation map, but write only to an in-memory DB.
    with sqlite3.connect(f.DB.as_uri() + "?mode=ro", uri=True) as source:
        memory = sqlite3.connect(":memory:")
        source.backup(memory)
    try:
        translations = f.import_translations(memory, BASELINE)
        return set("".join(target for target, _ in translations.values()))
    finally:
        memory.close()


def dialogue_colors():
    original = (BASELINE / "Data/Scripts.rxdata").read_bytes()
    code = next(zlib.decompress(blob).decode("utf-8") for _,name,blob in f.loads(original)
                if f.text(name) == "Messages")
    colors = {key: value for key,value,_ in re.findall(
        r'text\.gsub!\(/\\\\([br])/i,"<c3=([0-9A-F]{6}),([0-9A-F]{6})>"', code)}
    assert colors == {"b": "3050C8", "r": "E00808"}, "Original message color mapping changed"
    return {key: [*bytes.fromhex(value),255] for key,value in colors.items()}


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    coverage = json.loads((f.ROOT / "coverage.json").read_text(encoding="utf-8"))
    characters = target_characters()
    assert len(characters) == coverage["font"]["checked_characters"] == 3195
    colors = dialogue_colors()
    report = {"passed": False, "sample_only": True, "game_started": False, "installed": False,
              "canvas": [512,384], "scales": [1,3.75], "resampling": "NEAREST",
              "synthetic_bold": False, "offset_overpaint": False,
              "language_sha256": coverage["language_sha256"], "scripts_sha256": coverage["scripts_sha256"],
              "installed_font_sha256": coverage["font"]["sha256"], "dialogue_colors": colors,
              "freetype_version": features.version_module("freetype2"),
              "game_sdl_ttf_direct_load_tested": False,
              "game_sdl_ttf_note": "SDL_ttf is statically bundled in Game.exe; no separate game SDL_ttf DLL. Game.exe was not loaded or started. Pillow/FreeType loading does not prove the game path.",
              "renderer_sha256": f.digest((f.ROOT / "tools/font_preview.py").read_bytes()),
              "tool_sha256": f.digest(Path(__file__).read_bytes()), "fonts": [], "comparisons": []}
    panels = {name: [] for name in ("blue-dialogue", "red-dialogue", "orange-settings", "dark-smalltext")}
    for key,label,path,expected,weight,license_name in FONTS:
        assert f.digest(path.read_bytes()) == expected, f"Wrong local font: {path}"
        with TTFont(path,fontNumber=0) as face:
            missing = sorted(c for c in characters if ord(c) >= 32 and ord(c) not in face.getBestCmap())
            assert not missing, f"Missing glyphs in {label}: {missing}"
            assert face["OS/2"].usWeightClass == weight
            font_report = {"id": key, "label": label, "path": str(path), "sha256": expected,
                "weight": weight, "family": face["name"].getDebugName(1),
                "style": face["name"].getDebugName(2), "CFF": "CFF " in face,
                "checked_characters": len(characters), "missing": missing,
                "rare_characters": {c: ord(c) in face.getBestCmap() for c in "戽桄"},
                "license": license_name, "public_font_distribution": key == "a", "sizes": {}, "scenes": {}}
        for pixels in (12,24):
            font = ImageFont.truetype(str(path),pixels,index=0,layout_engine=ImageFont.Layout.BASIC)
            probe = "繁體中文：戽斗尖梭與桄榔島，歡迎來到寶可夢的世界！"
            mask = bytes(font.getmask(probe,mode="L"))
            font_report["sizes"][str(pixels)] = {"direct_load": True, "metrics": font.getmetrics(),
                "probe_advance": font.getlength(probe), "alpha_values": len(set(mask)),
                "latin_advance": font.getlength("Pikachu HP PP"),
                "fullscreen_advance": font.getlength("全螢幕"),
                "ink_area_px": sum(mask)/255.0}
        command = [sys.executable,"-B",str(f.ROOT / "tools/verify_ruby.py"),"--game",str(BASELINE),
                   "--font-sample",str(path)]
        result = subprocess.run(command,capture_output=True,encoding="utf-8")
        folder = DATA / key
        folder.mkdir(parents=True,exist_ok=True)
        native_log = LOGS / f"{key}-native-ruby.log"
        native_log.write_text(result.stdout+result.stderr,encoding="utf-8")
        if result.returncode:
            raise RuntimeError(f"{label}: native layout/painter failed; see {native_log}")
        for filename in ("validation.json","font-preview-layout.json","font-preview-draw-calls.json"):
            shutil.copy2(WORK / "smooth-font-sample" / filename, folder / filename)
        validation = json.loads((folder / "validation.json").read_text(encoding="utf-8"))
        assert validation["passed"] and validation["sample_only"] and validation["font_sha256"] == expected
        recorded = json.loads((folder / "font-preview-draw-calls.json").read_text(encoding="utf-8"))
        contexts = [
            ("blue-dialogue","dialogue-after",colors["b"],(248,248,248)),
            ("red-dialogue","dialogue-after",colors["r"],(248,248,248)),
            ("orange-settings","settings-after",None,None),
            ("dark-smalltext","smalltext-after",None,None)]
        for group,native_scene,color,background in contexts:
            calls = [dict(call, color=color or call["color"]) for call in recorded["scenes"][native_scene]]
            # Context colors are original Messages' main colors; positions stay native.
            canvas,bounds,alpha = paint_scene(native_scene,calls,path,validation["family"],True,background)
            collisions = [(left["text"],right["text"]) for i,left in enumerate(bounds) for right in bounds[i+1:]
                if max(left["box"][0],right["box"][0]) < min(left["box"][2],right["box"][2])
                and max(left["box"][1],right["box"][1]) < min(left["box"][3],right["box"][3])]
            assert not collisions, (label,group,"Overlapping ink bounds",collisions)
            for scale in (1,3.75):
                save_preview(canvas.resize((int(512*scale),int(384*scale)),Image.Resampling.NEAREST),
                             OUTPUT / f"{key}-{group}-{scale}x.png")
            crop = canvas.crop((0,8 if group == "orange-settings" else 256,512,376))
            save_preview(crop.resize((1920,int(crop.height*3.75)),Image.Resampling.NEAREST),
                         OUTPUT / f"{key}-{group}-crop-3.75x.png")
            panel = Image.new("RGB",(512,crop.height+24),(248,248,248))
            panel.paste(crop,(0,24))
            ImageDraw.Draw(panel).text((16,5),label,fill=(24,24,24))
            panels[group].append(panel)
            font_report["scenes"][group] = {"bounds_checked": len(bounds),"collisions": collisions,
                "horizontal_squeeze_cases": 0,"alpha_value_count": len(alpha),
                "text_color_override": color,"bounds": bounds}
        report["fonts"].append(font_report)
    for group,columns in panels.items():
        assert len(columns) == 3 and len({im.size for im in columns}) == 1
        comparison = Image.new("RGB",(1536,columns[0].height))
        for index,panel in enumerate(columns):
            comparison.paste(panel,(512*index,0))
        for scale in (1,3.75):
            path = OUTPUT / f"{group}-abc-{scale}x.png"
            save_preview(comparison.resize((int(1536*scale),int(comparison.height*scale)),Image.Resampling.NEAREST),path)
            report["comparisons"].append(str(path))
    report["passed"] = True
    f.json_write(DATA / "validation.json",report)
    print("PASS: A/B/C native layout; 3,195 characters each, missing=0; four scenes; 1x/3.75x NEAREST; no build/install")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        f.json_write(DATA / "validation.json",{"passed": False,"sample_only": True,
            "error": str(error),"game_started": False,"installed": False})
        raise
