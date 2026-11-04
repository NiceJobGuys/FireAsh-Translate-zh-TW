"""Export reviewable script diffs from the exact distribution snapshot (no game archive)."""
import argparse
import difflib
from pathlib import Path
import sys
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fire_ash import loads, text
from build import SCRIPT_SHA
from installer import digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--installed', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    current = args.installed.read_bytes()
    if digest(current) != SCRIPT_SHA:
        raise ValueError('Snapshot mismatch')
    before = {text(row[1]): zlib.decompress(row[2]).decode('utf-8-sig') for row in loads(args.baseline.read_bytes())}
    after = {text(row[1]): zlib.decompress(row[2]).decode('utf-8-sig') for row in loads(current)}
    diff = []
    names = []
    for name in sorted(before.keys() | after.keys()):
        old, new = before.get(name, ''), after.get(name, '')
        if old == new:
            continue
        names.append(name)
        diff.extend(difflib.unified_diff(old.splitlines(keepends=True), new.splitlines(keepends=True),
                                        fromfile='original/' + name + '.rb', tofile='extras/' + name + '.rb'))
        diff.append('\n')
    args.output.write_text(''.join(diff), encoding='utf-8')
    print('Changed script blocks:', len(names), ', '.join(names))


if __name__ == '__main__':
    main()
