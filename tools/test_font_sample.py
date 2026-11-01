"""Check that experimental font samples cannot replace the shipped reports/assets."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest
import mmap
import uuid

from PIL import Image, ImageChops

from fire_ash import ARTIFACTS, ROOT, GAME, staged_font_path
from font_preview import paint_scene, save_preview

WORK = ARTIFACTS / "data/fire-ash-work"
SAMPLE = WORK / "smooth-font-sample"
BASELINE = WORK / "original-baseline"
FONT = Path(r"C:\Windows\Fonts\msjh.ttc")
PROTECTED = [ROOT / name for name in (
    "coverage.json", "validation.json", "deployment-validation.json", "font-preview-validation.json",
    "runtime-coverage-validation.json", "text-buffer-validation.json", "command-window-validation.json",
    "battle-ui-validation.json")]
PROTECTED += [WORK / name for name in (
    "font-preview-layout.json", "font-preview-draw-calls.json", "patched/Scripts.rxdata")]
PROTECTED += [staged_font_path(json.loads(
    (ROOT / "coverage.json").read_text(encoding="utf-8"))["font"].get("profile","pixel"))]
PROTECTED += [WORK / "fonts" / json.loads(
    (ROOT / "coverage.json").read_text(encoding="utf-8"))["font"].get("license_notice_file", "fire-ash-zhtw-OFL.txt")]
PROTECTED += [ARTIFACTS / "release/fire-ash-zh-tw-preview/Data/traditional_chinese.dat"]
PROTECTED += [Path(path) for path in json.loads(
    (ROOT / "font-preview-validation.json").read_text(encoding="utf-8"))["previews"]]


def hashes():
    return {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in PROTECTED}


class FontSampleTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform == "win32","Windows mapped-image regression")
    def test_mapped_preview_keeps_identical_image(self):
        folder = ARTIFACTS / "images/fire-ash/preview-write-fixtures"
        folder.mkdir(parents=True,exist_ok=True)
        path = folder / f"lock-{uuid.uuid4().hex}.png"
        sample = Image.new("RGB",(8,8),(48,80,200))
        sample.save(path)
        before = path.read_bytes()
        with path.open("rb") as handle:
            with mmap.mmap(handle.fileno(),0,access=mmap.ACCESS_READ):
                with self.assertRaises(OSError) as raised:
                    sample.save(path)
                self.assertEqual(raised.exception.errno,22)
                save_preview(sample,path)
                self.assertEqual(path.read_bytes(),before)

    def run_sample(self, font):
        return subprocess.run([sys.executable, str(ROOT / "tools/verify_ruby.py"),
                               "--game", str(BASELINE), "--font-sample", str(font)],
                              capture_output=True, encoding="utf-8")

    def test_missing_font_keeps_production_reports(self):
        missing = SAMPLE / "not-present.ttf"
        self.assertFalse(missing.exists())
        before = hashes()
        result = self.run_sample(missing)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(json.loads((SAMPLE / "validation.json").read_text(encoding="utf-8"))["passed"])
        self.assertEqual(hashes(), before)

    def test_shared_painter_matches_recorded_previews(self):
        coverage = json.loads((ROOT / "coverage.json").read_text(encoding="utf-8"))
        recorded = json.loads((WORK / "font-preview-draw-calls.json").read_text(encoding="utf-8"))
        profile = coverage["font"].get("profile", "pixel")
        font = staged_font_path(profile)
        for scene,calls in recorded["scenes"].items():
            with self.subTest(scene=scene):
                profile = coverage["font"].get("profile", "pixel")
                suffix = ("three-shadows-only" if scene.endswith("before") else
                          f"{profile}-trial" if profile in ("jhenghei","noto") else "no-shadow-only")
                path = ARTIFACTS / "images/fire-ash" / f"font-preview-{scene.rsplit('-',1)[0]}-{suffix}-1x.png"
                canvas,_,_ = paint_scene(scene,calls,font,coverage["font"]["family"],profile in ("jhenghei","noto"))
                expected = Image.open(path).convert("RGB")
                self.assertIsNone(ImageChops.difference(canvas,expected).getbbox(), str(path))

    def test_weight_samples_keep_production_reports_and_assets(self):
        before = hashes()
        installed = [GAME / p for p in ("Data/Scripts.rxdata","Data/traditional_chinese.dat",
            "Fonts/fire-ash-zhtw.ttf","Fonts/fire-ash-zhtw.otf","Fonts/fire-ash-zhtw-OFL.txt",
            "Fonts/fire-ash-zhtw-LOCAL-ONLY.txt","Game.exe","Game.ini","mkxp.json") if (GAME / p).exists()]
        installed_before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in installed}
        result = subprocess.run([sys.executable,"-B",str(ROOT / "tools/weight_sample.py")],
                                capture_output=True,encoding="utf-8")
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        report = json.loads((WORK / "weight-sample/validation.json").read_text(encoding="utf-8"))
        self.assertTrue(report["passed"] and report["sample_only"])
        self.assertFalse(report["synthetic_bold"] or report["offset_overpaint"])
        self.assertEqual([row["weight"] for row in report["fonts"]],[500,700,400])
        coverage = json.loads((ROOT / "coverage.json").read_text(encoding="utf-8"))
        for row in report["fonts"]:
            self.assertEqual(row["checked_characters"],coverage["font"]["checked_characters"])
            self.assertEqual(row["missing"],[])
            self.assertTrue(all(row["rare_characters"].values()))
        self.assertEqual(len(report["comparisons"]),8)
        for group in ("blue-dialogue","red-dialogue","orange-settings","dark-smalltext"):
            images = ARTIFACTS / "images/fire-ash/weight-sample"
            first = Image.open(images / f"{group}-abc-1x.png").convert("RGB")
            enlarged = Image.open(images / f"{group}-abc-3.75x.png").convert("RGB")
            self.assertEqual(enlarged.width,5760)
            expected = first.resize(enlarged.size,Image.Resampling.NEAREST)
            self.assertIsNone(ImageChops.difference(enlarged,expected).getbbox())
            a = Image.open(images / f"a-{group}-1x.png").convert("RGB")
            b = Image.open(images / f"b-{group}-1x.png").convert("RGB")
            c = Image.open(images / f"c-{group}-1x.png").convert("RGB")
            self.assertIsNotNone(ImageChops.difference(a,c).getbbox())
            self.assertIsNotNone(ImageChops.difference(b,c).getbbox())
        self.assertEqual(hashes(),before)
        self.assertEqual(installed_before,{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in installed})

    def test_success_keeps_production_reports_and_assets(self):
        before = hashes()
        result = self.run_sample(FONT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        result = subprocess.run([sys.executable, str(ROOT / "tools/font_preview.py"),
                                 "--font-sample", str(FONT)], capture_output=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        validation = json.loads((SAMPLE / "validation.json").read_text(encoding="utf-8"))
        preview = json.loads((SAMPLE / "preview-validation.json").read_text(encoding="utf-8"))
        self.assertTrue(validation["sample_only"] and validation["passed"])
        self.assertEqual(validation["missing_characters"], [])
        self.assertTrue(preview["sample_only"] and preview["passed"])
        self.assertGreater(preview["alpha_value_count"], 2, "Smooth sample was thresholded into a pixel font")
        self.assertEqual(hashes(), before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
