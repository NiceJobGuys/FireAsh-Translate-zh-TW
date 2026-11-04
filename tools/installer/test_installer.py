"""Transaction regression tests using isolated copies, never the player's installation."""
import json
import os
from pathlib import Path
import shutil
import sys
import unittest
from unittest.mock import patch
import uuid

import installer as app

ROOT = Path(os.environ['FIREASH_TEST_ROOT']).resolve()
BASELINE = Path(os.environ['FIREASH_BASELINE']).resolve()
INSTALLED = Path(os.environ['FIREASH_INSTALLED']).resolve()
app.PAYLOAD = Path(os.environ['FIREASH_PAYLOAD']).resolve()


def fixture(destination):
    destination.mkdir(parents=True)
    manifest, _ = app.package()
    for relative in manifest['baseline']:
        source = BASELINE / relative
        if not source.is_file():
            source = INSTALLED / relative
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    (destination / 'Save.rxdata').write_bytes(b'player save sentinel')
    return destination


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.game = fixture(ROOT / uuid.uuid4().hex)
        self.manifest, _ = app.package()
        self.closed = patch.object(app, 'require_closed')
        self.closed.start()

    def tearDown(self):
        self.closed.stop()
        self.assertEqual((self.game / 'Save.rxdata').read_bytes(), b'player save sentinel')

    def install(self):
        return app.run('install', self.game, INSTALLED / 'Fonts')

    def original(self):
        for relative, expected in self.manifest['baseline'].items():
            self.assertEqual(app.file_hash(self.game / relative), expected, relative)
        for relative in app.FILES[1:]:
            self.assertFalse((self.game / relative).exists(), relative)

    def test_install_repeat_restore_reinstall(self):
        self.assertEqual(self.install()['status'], 'installed')
        for relative, expected in self.manifest['installed'].items():
            self.assertEqual(app.file_hash(self.game / relative), expected)
        self.assertEqual(self.install()['status'], 'already_installed')
        self.assertEqual(app.run('restore', self.game)['status'], 'restored')
        self.original()
        self.assertEqual(app.run('restore', self.game)['status'], 'restored')
        self.assertEqual(self.install()['status'], 'installed')

    def test_unknown_version_refused(self):
        (self.game / 'Game.ini').write_text('wrong version')
        with self.assertRaisesRegex(ValueError, '版本'):
            self.install()
        self.assertFalse((self.game / app.BACKUP).exists())

    def test_other_mod_refused(self):
        (self.game / app.FILES[0]).write_bytes(b'other mod')
        with self.assertRaisesRegex(ValueError, '其他 MOD'):
            self.install()
        self.assertEqual((self.game / app.FILES[0]).read_bytes(), b'other mod')

    def test_copy_failure_rolls_back(self):
        replace = app.os.replace
        failed = False
        def fail_once(source, target):
            nonlocal failed
            if not failed and Path(target) == self.game / app.FILES[1]:
                failed = True
                raise OSError('simulated full disk')
            return replace(source, target)
        with patch.object(app.os, 'replace', side_effect=fail_once):
            with self.assertRaisesRegex(OSError, 'full disk'):
                self.install()
        self.original()
        self.assertFalse((self.game / 'FireAsh-Extras.lock').exists())

    def test_corrupt_font_refused_before_backup(self):
        with patch.object(app, 'font_bytes', return_value=b'bad font'):
            with self.assertRaisesRegex(ValueError, '校驗'):
                self.install()
        self.original()
        self.assertFalse((self.game / app.BACKUP).exists())

    def test_network_failure_before_backup(self):
        with patch.object(app.urllib.request, 'urlopen', side_effect=OSError('offline')):
            with self.assertRaisesRegex(OSError, 'offline'):
                app.run('install', self.game)
        self.original()

    def test_changed_file_blocks_restore(self):
        self.install()
        (self.game / app.FILES[1]).write_bytes(b'user change')
        with self.assertRaisesRegex(ValueError, '其他修改'):
            app.run('restore', self.game)
        self.assertEqual(app.file_hash(self.game / app.FILES[0]), self.manifest['installed'][app.FILES[0]])

    def test_corrupt_backup_blocks_restore(self):
        result = self.install()
        (Path(result['backup']) / 'original' / app.FILES[0]).write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError, '備份損壞'):
            app.run('restore', self.game)
        self.assertEqual(app.file_hash(self.game / app.FILES[0]), self.manifest['installed'][app.FILES[0]])

    def test_game_running_blocks_install(self):
        with patch.object(app, 'require_closed', side_effect=ValueError('game is running')):
            with self.assertRaisesRegex(ValueError, 'running'):
                self.install()
        self.original()

    def test_concurrent_install_lock(self):
        lock = self.game / 'FireAsh-Extras.lock'
        lock.touch()
        with self.assertRaisesRegex(ValueError, '另一個'):
            self.install()
        self.assertTrue(lock.exists())
        self.original()

    def test_interrupted_install_restore(self):
        result = self.install()
        folder = Path(result['backup'])
        record = app.read_json(folder / 'manifest.json')
        record['status'] = 'prepared'
        app.write_json(folder / 'manifest.json', record)
        # Simulate an interrupted transaction after only Scripts was replaced.
        for relative in app.FILES[1:]:
            os.replace(self.game / relative, folder / ('interrupted-' + Path(relative).name))
        self.assertEqual(app.run('restore', self.game)['status'], 'restored')
        self.original()

    def test_traversal_rejected(self):
        with self.assertRaises(ValueError):
            app.safe(self.game, '../escape')
        with self.assertRaises(ValueError):
            app.safe(self.game, str(ROOT))


if __name__ == '__main__':
    unittest.main(verbosity=2)
