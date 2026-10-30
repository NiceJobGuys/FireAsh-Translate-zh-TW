"""Filesystem-only fixtures. Never deploys to or starts the installed game."""
import argparse
import json
import datetime
import shutil
import sys
import unittest
from unittest.mock import patch

import install_preview as deploy

RUN_ID = "run-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
SOURCE_GAME = deploy.GAME
# Pin the historical schema independently of any future installer FILES changes.
LEGACY_FOUR_FILES = ("Data/Scripts.rxdata", "Data/traditional_chinese.dat",
                     "Fonts/fire-ash-zhtw.ttf", "Fonts/fire-ash-zhtw-OFL.txt")


class DeploymentTests(unittest.TestCase):
    def setUp(self):
        self.root = deploy.ARTIFACTS / "data/fire-ash-work/install-fixtures" / RUN_ID / self._testMethodName
        self.root.mkdir(parents=True, exist_ok=False)
        manifest = json.loads((deploy.ROOT / "source-manifest.json").read_text(encoding="utf-8"))
        for relative in manifest["files"]:
            target = deploy.within(self.root, relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(SOURCE_GAME / relative, target)
        self.backup = deploy.BACKUPS / "fire-ash-zhtw-install-fixtures" / RUN_ID / self._testMethodName
        self.assertFalse(self.backup.exists(), "Fixture already exists; keep its evidence and use a fresh path.")

    def test_install_restore(self):
        with self.assertRaisesRegex(ValueError, "Path leaves its root"):
            deploy.within(self.root, "../outside-fixture")
        before = sorted(str(p.relative_to(self.root)) for p in self.root.rglob("*") if p.is_file())
        plan = deploy.plan(self.root)
        self.assertEqual(before, sorted(str(p.relative_to(self.root)) for p in self.root.rglob("*") if p.is_file()))
        result = deploy.install(self.root, self.backup)
        self.assertFalse(result["game_started"])
        for row in plan["files"]:
            self.assertEqual(deploy.sha(self.root / row["relative"]), row["installed_sha256"])
        deploy.restore(self.backup)
        self.assertEqual(deploy.sha(self.root / deploy.FILES[0]), plan["files"][0]["original_sha256"])
        self.assertFalse((self.root / deploy.FILES[1]).exists())
        self.assertFalse((self.root / deploy.FILES[2]).exists())
        self.assertEqual(before, sorted(str(p.relative_to(self.root)) for p in self.root.rglob("*") if p.is_file()))
        baseline = json.loads((deploy.ROOT / "source-manifest.json").read_text(encoding="utf-8"))
        for relative, expected in baseline["files"].items():
            self.assertEqual(deploy.sha(self.root / relative), expected)

    def test_refuse_changed_file(self):
        deploy.install(self.root, self.backup)
        target = self.root / deploy.FILES[1]
        target.write_bytes(b"user-edited-file")
        with self.assertRaisesRegex(ValueError, "套用後又被修改"):
            deploy.restore(self.backup)
        self.assertEqual(target.read_bytes(), b"user-edited-file")
        # Return the fixture to its initial state after verifying the refusal.
        built = deploy.ARTIFACTS / "release/fire-ash-zh-tw-preview/Data/traditional_chinese.dat"
        shutil.copy2(built, target)
        deploy.restore(self.backup)

    def restore_legacy_manifest(self, relative_paths):
        before = {str(p.relative_to(self.root)): deploy.sha(p)
                  for p in self.root.rglob("*") if p.is_file()}
        # Reproduce the original installer format, then use the current restore.
        with patch.object(deploy, "FILES", relative_paths):
            deploy.install(self.root, self.backup)
        manifest_bytes = (self.backup / "manifest.json").read_bytes()
        self.assertEqual(tuple(row["relative"] for row in json.loads(manifest_bytes)["files"]), relative_paths)
        deploy.restore(self.backup)
        self.assertEqual(manifest_bytes, (self.backup / "manifest.json").read_bytes())
        after = {str(p.relative_to(self.root)): deploy.sha(p)
                 for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_restore_legacy_three_file_manifest(self):
        self.restore_legacy_manifest(LEGACY_FOUR_FILES[:3])

    def test_restore_legacy_four_file_manifest(self):
        self.restore_legacy_manifest(LEGACY_FOUR_FILES)

    def test_refuse_unknown_or_incomplete_manifest(self):
        deploy.install(self.root, self.backup)
        manifest_path = self.backup / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        entries = manifest["files"]
        before = {str(p.relative_to(self.root)): deploy.sha(p)
                  for p in self.root.rglob("*") if p.is_file()}
        unsafe = dict(entries[-1], relative="../outside-fixture")
        unknown = dict(entries[-1], relative="Data/unknown.dat")
        for bad in (entries[:2], entries + [unknown], entries + [entries[0]], entries[:3] + [unsafe]):
            with self.subTest(paths=[row["relative"] for row in bad]):
                deploy.json_write(manifest_path, dict(manifest, files=bad))
                with self.assertRaisesRegex(ValueError, "備份清單"):
                    deploy.restore(self.backup)
                self.assertEqual(before, {str(p.relative_to(self.root)): deploy.sha(p)
                                          for p in self.root.rglob("*") if p.is_file()})
        deploy.json_write(manifest_path, manifest)
        deploy.restore(self.backup)

    def test_failed_install_rolls_back(self):
        original = deploy.sha(self.root / deploy.FILES[0])
        copy = shutil.copy2

        def fail_language(source, destination, *args, **kwargs):
            if str(source).endswith("traditional_chinese.dat"):
                destination.write_bytes(b"incomplete-copy")
                raise OSError("fixture copy failure")
            return copy(source, destination, *args, **kwargs)

        with patch.object(deploy.shutil, "copy2", side_effect=fail_language):
            with self.assertRaisesRegex(OSError, "fixture copy failure"):
                deploy.install(self.root, self.backup)
        self.assertEqual(deploy.sha(self.root / deploy.FILES[0]), original)
        self.assertFalse((self.root / deploy.FILES[1]).exists())
        self.assertFalse((self.root / (deploy.FILES[1] + ".fire-ash-zhtw-part")).exists())
        self.assertEqual((self.backup / "failed-stage" / (deploy.FILES[1] + ".fire-ash-zhtw-part")).read_bytes(),
                         b"incomplete-copy")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-game", type=deploy.Path, default=deploy.GAME)
    args = parser.parse_args()
    SOURCE_GAME = args.source_game.resolve()
    original = json.loads((deploy.ROOT / "source-manifest.json").read_text(encoding="utf-8"))
    for relative, expected in original["files"].items():
        assert deploy.sha(SOURCE_GAME / relative) == expected, f"Original baseline changed: {relative}"
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(DeploymentTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    baseline = json.loads((deploy.ROOT / "source-manifest.json").read_text(encoding="utf-8"))
    unchanged = all(deploy.sha(SOURCE_GAME / relative) == expected for relative, expected in baseline["files"].items())
    deploy.json_write(deploy.ROOT / "deployment-validation.json", {
        "passed": result.wasSuccessful() and unchanged, "tests_run": result.testsRun,
        "failures": len(result.failures), "errors": len(result.errors),
        "source_game_unchanged": unchanged, "game_started": False,
        "scope": "僅在Artifacts內的檔案測試副本套用及還原；未套用到安裝目錄，未啟動遊戲。",
        "fixture_run": RUN_ID, "installer_sha256": deploy.sha(deploy.ROOT / "tools/install_preview.py"),
        "source_baseline": str(SOURCE_GAME), "font_sha256": deploy.sha(
            deploy.ARTIFACTS / "data/fire-ash-work/fonts/fire-ash-zhtw.ttf"),
        "scripts_sha256": deploy.sha(deploy.ARTIFACTS / "data/fire-ash-work/patched/Scripts.rxdata"),
        "test_sha256": deploy.sha(__file__), "language_sha256": deploy.sha(
            deploy.ARTIFACTS / "release/fire-ash-zh-tw-preview/Data/traditional_chinese.dat")})
    sys.exit(0 if result.wasSuccessful() and unchanged else 1)
