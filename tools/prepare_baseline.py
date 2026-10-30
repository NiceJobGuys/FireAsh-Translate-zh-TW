"""Assemble a hash-checked build fixture without changing the installed game."""
import json
import shutil

from fire_ash import ARTIFACTS, GAME, ROOT, digest


def main():
    destination = ARTIFACTS / "data/fire-ash-work/original-baseline"
    backup = ARTIFACTS / "backup/fire-ash-zhtw-before-install-20261030/original"
    manifest = json.loads((ROOT / "source-manifest.json").read_text(encoding="utf-8"))
    for relative, expected in manifest["files"].items():
        saved = backup / relative
        source = saved if saved.exists() else GAME / relative
        if digest(source.read_bytes()) != expected:
            raise ValueError(f"Baseline source hash mismatch: {source}")
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        assert digest(target.read_bytes()) == expected
    print(f"PASS: {len(manifest['files'])} original files verified at {destination}")


if __name__ == "__main__":
    main()
