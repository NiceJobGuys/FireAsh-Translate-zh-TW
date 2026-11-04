"""Exercise the actual EXE with an empty PATH and isolated game fixtures."""
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

from test_installer import ROOT, fixture, app


def main():
    exe = Path(sys.argv[1]).resolve()
    game = fixture(ROOT / ('standalone-中文路徑-' + uuid.uuid4().hex[:8]))
    runtime = ROOT / 'runtime'
    runtime.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, PATH='', PYTHONPATH='', PYTHONHOME='', TEMP=str(runtime), TMP=str(runtime))
    logs = []
    for action in ('check', 'install', 'install', 'restore', 'check'):
        report = ROOT / ('exe-' + str(len(logs)) + '.json')
        # Installation intentionally downloads the font; no development files are passed.
        command = [str(exe), '--action', action, '--game', str(game), '--report', str(report)]
        result = subprocess.run(command, env=env, timeout=180, creationflags=0x08000000)
        data = json.loads(report.read_text(encoding='utf-8'))
        if result.returncode:
            raise RuntimeError(data)
        logs.append({'action': action, 'exit_code': result.returncode, **data})
    assert [entry['status'] for entry in logs] == ['ready', 'installed', 'already_installed', 'restored', 'ready']
    assert (game / 'Save.rxdata').read_bytes() == b'player save sentinel'
    manifest, _ = app.package()
    for relative, expected in manifest['baseline'].items():
        assert app.file_hash(game / relative) == expected, relative
    result = subprocess.run([str(exe), '--gui-smoke'], env=env, timeout=30, creationflags=0x08000000)
    assert result.returncode == 0, 'Bundled Tk initialization failed'
    summary = {'exe_sha256': app.file_hash(exe), 'empty_path': True, 'font_download': True,
               'unicode_path': True, 'gui_initialization': True, 'save_preserved': True,
               'original_restored': True, 'game_started': False, 'runs': logs}
    (ROOT / 'standalone-validation.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
