"""Check that experimental font samples cannot replace the shipped reports/assets."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

from fire_ash import ARTIFACTS, ROOT

WORK = ARTIFACTS / "data/fire-ash-work"
SAMPLE = WORK / "smooth-font-sample"
BASELINE = WORK / "original-baseline"
FONT = Path(r"C:\Windows\Fonts\msjh.ttc")
PROTECTED = [ROOT / name for name in (
    "coverage.json", "validation.json", "deployment-validation.json", "font-preview-validation.json")]
PROTECTED += [WORK / name for name in (
    "font-preview-layout.json", "font-preview-draw-calls.json", "patched/Scripts.rxdata",
    "fonts/fire-ash-zhtw.ttf", "fonts/fire-ash-zhtw-OFL.txt")]
PROTECTED += [ARTIFACTS / "release/fire-ash-zh-tw-preview/Data/traditional_chinese.dat"]
PROTECTED += [Path(path) for path in json.loads(
    (ROOT / "font-preview-validation.json").read_text(encoding="utf-8"))["previews"]]


def hashes():
    return {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in PROTECTED}


class FontSampleTests(unittest.TestCase):
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
