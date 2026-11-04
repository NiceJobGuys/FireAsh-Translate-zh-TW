"""Build a hash-pinned distribution from an original baseline and verified installation."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

import bsdiff4

from installer import FILES, digest

VERSION = '3.7-extras.1'
SCRIPT_SHA = '482efd03585fca9060f6dae9aed06a2f753e674b912aa7d8ed683a3eb9390668'
LANGUAGE_SHA = 'd4cc61cdd16be413cca6838f2f9d8401945bce6339e2586b5d918076af414edf'
FONT_COMMIT = 'f8d157532fbfaeda587e826d4cd5b21a49186f7c'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--installed', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[2]
    baseline = json.loads((repo / 'source-manifest.json').read_text(encoding='utf-8'))['files']
    for relative, expected in baseline.items():
        if digest((args.baseline / relative).read_bytes()) != expected:
            raise ValueError('Baseline mismatch: ' + relative)
    original = (args.baseline / FILES[0]).read_bytes()
    current = (args.installed / FILES[0]).read_bytes()
    language = (args.installed / FILES[1]).read_bytes()
    if digest(current) != SCRIPT_SHA or digest(language) != LANGUAGE_SHA:
        raise ValueError('Installed snapshot changed; review and version the new release first.')
    font = json.loads((repo / 'font-source-noto.json').read_text(encoding='utf-8'))
    for relative, key in ((FILES[2], 'sha256'), (FILES[3], 'license_sha256')):
        if digest((args.installed / relative).read_bytes()) != font[key]:
            raise ValueError('Font/license mismatch: ' + relative)
    assets = {'scripts.bsdiff': bsdiff4.diff(original, current), 'language.dat': language,
              'font-license.txt': (args.installed / FILES[3]).read_bytes()}
    if bsdiff4.patch(original, assets['scripts.bsdiff']) != current:
        raise ValueError('Patch round-trip failed.')
    for relative in ('Game.exe', 'Data/PluginScripts.rxdata'):
        baseline[relative] = digest((args.installed / relative).read_bytes())
    if baseline['Game.exe'] != font['engine_binary_sha256']:
        raise ValueError('Engine binary changed.')
    installed = {relative: digest((args.installed / relative).read_bytes()) for relative in FILES}
    manifest = {'version': VERSION, 'baseline': baseline, 'installed': installed,
                'assets': {name: digest(data) for name, data in assets.items()},
                'font': {'size': (args.installed / FILES[2]).stat().st_size,
                         'url': 'https://raw.githubusercontent.com/notofonts/noto-cjk/' + FONT_COMMIT + '/Sans/OTF/TraditionalChinese/NotoSansCJKtc-Medium.otf'},
                'game_started': False}
    args.work.mkdir(parents=True, exist_ok=True)
    args.output.mkdir(parents=True, exist_ok=True)
    payload = args.work / 'payload.zip'
    with zipfile.ZipFile(payload, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2))
        for name, data in assets.items():
            archive.writestr(name, data)
    (args.work / 'package-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onefile', '--windowed',
                    '--name', 'FireAsh-zhTW-' + VERSION, '--distpath', str(args.output),
                    '--workpath', str(args.work / 'pyinstaller'), '--specpath', str(args.work),
                    '--add-data', str(payload) + ';.',
                    '--add-data', str(Path(__file__).with_name('third-party-notices.txt')) + ';.',
                    str(Path(__file__).with_name('installer.py'))], check=True)
    exe = args.output / ('FireAsh-zhTW-' + VERSION + '.exe')
    (args.output / (exe.name + '.sha256')).write_text(hashlib.sha256(exe.read_bytes()).hexdigest() + '  ' + exe.name + '\n', encoding='ascii')
    print(json.dumps({'exe': str(exe), 'bytes': exe.stat().st_size, 'patch_bytes': len(assets['scripts.bsdiff']),
                      'font_embedded': False, 'original_game_embedded': False}, indent=2))


if __name__ == '__main__':
    main()
