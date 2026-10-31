"""Local preview deployment. Default plan is read-only; never starts the game."""
import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from fire_ash import ARTIFACTS, GAME, ROOT, digest, json_write

FILES = ("Data/Scripts.rxdata", "Data/traditional_chinese.dat", "Fonts/fire-ash-zhtw.ttf",
         "Fonts/fire-ash-zhtw-OFL.txt")
LEGACY_FILES = FILES[:3]
JH_FILES = FILES[:3] + ("Fonts/fire-ash-zhtw-LOCAL-ONLY.txt",)
NOTO_FILES = (FILES[0], FILES[1], "Fonts/fire-ash-zhtw.otf", FILES[3])
BACKUPS = ARTIFACTS / "backup"


def within(root, relative):
    root = Path(root).resolve()
    target = (root / relative).resolve()
    if target == root or not target.is_relative_to(root):
        raise ValueError(f"Path leaves its root: {target}")
    return target


def sha(path):
    return digest(Path(path).read_bytes())


def require_closed(game):
    if sys.platform != "win32":
        return
    result = subprocess.run([
        "pwsh", "-NoProfile", "-NonInteractive", "-Command",
        "@(Get-Process -Name Game -ErrorAction SilentlyContinue | ForEach-Object { "
        "try { if ($_.Path) { $_.Path } else { 'UNKNOWN' } } catch { 'UNKNOWN' } }) | ConvertTo-Json -Compress"
    ], capture_output=True, text=True, check=True)
    active = json.loads(result.stdout) if result.stdout.strip() else []
    active = [active] if isinstance(active, str) else active
    for path in active:
        if path == "UNKNOWN" or Path(path).resolve() == within(game, "Game.exe"):
            raise ValueError("請先正常退出遊戲，再套用或還原；工具不會關閉程序。")


def plan(game, font_source=None):
    game = Path(game).resolve()
    source = json.loads((ROOT / "source-manifest.json").read_text(encoding="utf-8"))
    coverage = json.loads((ROOT / "coverage.json").read_text(encoding="utf-8"))
    profile = coverage["font"].get("profile", "pixel")
    if profile not in ("pixel", "jhenghei", "noto") or (font_source and font_source != profile):
        raise ValueError("字型來源與建置報告不符；請先重建指定版本。")
    files = NOTO_FILES if profile == "noto" else JH_FILES if profile == "jhenghei" else FILES
    if any(row["pending_unique"] for row in coverage["sections"]):
        raise ValueError("仍有待翻項目，不允許安裝此預覽包。")
    for relative, expected in source["files"].items():
        if sha(within(game, relative)) != expected:
            raise ValueError(f"遊戲基準雜湊不符：{relative}")
    staged = (
        (ARTIFACTS / "data/fire-ash-work/patched/Scripts.rxdata", coverage["scripts_sha256"]),
        (ARTIFACTS / "release/fire-ash-zh-tw-preview/Data/traditional_chinese.dat", coverage["language_sha256"]),
        (ARTIFACTS / "data/fire-ash-work/fonts" / Path(files[2]).name, coverage["font"]["sha256"]),
        (ARTIFACTS / "data/fire-ash-work/fonts" / Path(files[3]).name, coverage["font"]["license_sha256"]),
    )
    entries = []
    for leftover in sorted(set(FILES + JH_FILES + NOTO_FILES) - set(files)):
        if within(game, leftover).exists():
            raise ValueError(f"另一字型的檔案仍存在；先用該次備份完整還原：{leftover}")
    for relative, (built, expected) in zip(files, staged):
        target = within(game, relative)
        if within(game, relative + ".fire-ash-zhtw-part").exists():
            raise ValueError(f"上次套用的暫存檔仍存在，請先檢查：{relative}.fire-ash-zhtw-part")
        if relative != FILES[0] and target.exists():
            raise ValueError(f"新檔案的路徑已存在，拒絕覆寫：{target}")
        if sha(built) != expected:
            raise ValueError(f"建置產物雜湊不符：{built}")
        entries.append({"relative": relative, "source": str(built), "installed_sha256": expected,
                        "original_sha256": sha(target) if target.exists() else None})
    return {"game": str(game), "files": entries, "font_source": profile,
            "local_trial_only": profile == "jhenghei", "game_ini_changed": False,
            "game_started": False, "backup_root": str(BACKUPS)}


def backup_path(path):
    path = Path(path).resolve()
    if path == BACKUPS.resolve() or not path.is_relative_to(BACKUPS.resolve()):
        raise ValueError(f"備份必須位於 {BACKUPS} 的子目錄：{path}")
    return path


def restore(backup):
    backup = backup_path(backup)
    manifest = json.loads((backup / "manifest.json").read_text(encoding="utf-8"))
    game = Path(manifest["game"]).resolve()
    entries = manifest["files"]
    if tuple(row["relative"] for row in entries) not in (LEGACY_FILES, FILES, JH_FILES, NOTO_FILES):
        raise ValueError("備份清單不是支援的舊版三檔、像素四檔、正黑體四檔或 Noto 四檔清單。")
    require_closed(game)
    # Validate every file before restoring any of them. User edits are never overwritten.
    for row in entries:
        target = within(game, row["relative"])
        if target.exists() and sha(target) not in {row["installed_sha256"], row["original_sha256"]}:
            raise ValueError(f"檔案在套用後又被修改，拒絕覆寫：{target}")
        if row["original_sha256"] and sha(within(backup, "original/" + row["relative"])) != row["original_sha256"]:
            raise ValueError(f"原檔備份雜湊不符：{row['relative']}")
    for row in entries:
        target = within(game, row["relative"])
        if row["original_sha256"]:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(within(backup, "original/" + row["relative"]), target)
            assert sha(target) == row["original_sha256"]
        elif target.exists():
            destination = within(backup, "removed-on-restore/" + row["relative"])
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                raise ValueError(f"還原封存路徑已存在：{destination}")
            shutil.move(str(target), str(destination))
    json_write(backup / "restored.json", {"game": str(game), "restored": True, "game_started": False})
    return {"restored": True, "game": str(game), "backup": str(backup), "game_started": False}


def install(game, backup=None, font_source=None):
    manifest = plan(game, font_source)
    require_closed(game)
    name = "fire-ash-zhtw-before-install-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup = backup_path(backup or BACKUPS / name)
    backup.mkdir(parents=True, exist_ok=False)
    # All original files are backed up and checked before the first game write.
    for row in manifest["files"]:
        if row["original_sha256"]:
            original = within(backup, "original/" + row["relative"])
            original.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(within(game, row["relative"]), original)
            if sha(original) != row["original_sha256"]:
                raise ValueError(f"備份校驗失敗：{original}")
    json_write(backup / "manifest.json", manifest)
    created_parts = []
    try:
        for row in manifest["files"]:
            target = within(game, row["relative"])
            target.parent.mkdir(parents=True, exist_ok=True)
            part = within(game, row["relative"] + ".fire-ash-zhtw-part")
            if part.exists():
                raise ValueError(f"暫存路徑已存在，拒絕覆寫：{part}")
            created_parts.append((row["relative"], part))
            shutil.copy2(row["source"], part)
            if sha(part) != row["installed_sha256"]:
                raise ValueError(f"套用暫存檔校驗失敗：{part}")
            os.replace(part, target)
    except Exception:
        # Incomplete copies never replace their destinations; keep their evidence in the backup.
        try:
            for relative, part in created_parts:
                if part.exists():
                    archived = within(backup, "failed-stage/" + relative + ".fire-ash-zhtw-part")
                    archived.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(part), str(archived))
            restore(backup)
        except Exception as rollback_error:
            print(f"自動還原未完成：{rollback_error}；原檔備份：{backup}", file=sys.stderr)
        raise
    return {"installed": True, "game": str(Path(game).resolve()), "backup": str(backup),
            "game_started": False, "game_ini_changed": False}


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", nargs="?", choices=("plan", "install", "restore"), default="plan")
    parser.add_argument("--game", type=Path, default=GAME)
    parser.add_argument("--backup", type=Path)
    parser.add_argument("--font-source", choices=("pixel", "jhenghei", "noto"),
                        help="Require the staged build to match this profile")
    args = parser.parse_args()
    if args.action == "restore" and args.backup is None:
        parser.error("restore 必須提供 --backup 的完整備份目錄")
    result = (plan(args.game, args.font_source) if args.action == "plan" else install(args.game, args.backup, args.font_source)
              if args.action == "install" else restore(args.backup))
    print(json.dumps(result, ensure_ascii=False, indent=2))
