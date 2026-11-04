"""Standalone Fire Ash extras installer; no shell, Python, or admin setup needed."""
import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import queue
import shutil
import sys
import threading
import urllib.request
import uuid
import zipfile

import bsdiff4

FILES = ('Data/Scripts.rxdata', 'Data/traditional_chinese.dat',
         'Fonts/fire-ash-zhtw.otf', 'Fonts/fire-ash-zhtw-OFL.txt')
BACKUP = 'FireAsh-Extras-backup'
PAYLOAD = Path(__file__).with_name('payload.zip')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe(root, relative):
    root = Path(root).resolve()
    target = root / relative
    if Path(relative).is_absolute() or '..' in Path(relative).parts:
        raise ValueError('無效的相對路徑。')
    for part in (target, *target.parents):
        if part == root:
            break
        if part.is_symlink() or (hasattr(part, 'is_junction') and part.is_junction()):
            raise ValueError('不支援符號連結或 junction：' + str(part))
    if not target.resolve().is_relative_to(root) or target.resolve() == root:
        raise ValueError('路徑超出遊戲資料夾。')
    return target


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path, data):
    # Metadata is atomically replaced, including the recovery record.
    temp = path.with_name(path.name + '.tmp')
    with temp.open('x', encoding='utf-8') as output:
        json.dump(data, output, ensure_ascii=False, indent=2)
    os.replace(temp, path)


def require_closed():
    """Conservatively reject any Game.exe, without PowerShell or psutil."""
    if sys.platform != 'win32':
        return
    class Entry(ctypes.Structure):
        _fields_ = [('dwSize', wintypes.DWORD), ('cntUsage', wintypes.DWORD),
                    ('th32ProcessID', wintypes.DWORD), ('th32DefaultHeapID', ctypes.c_size_t),
                    ('th32ModuleID', wintypes.DWORD), ('cntThreads', wintypes.DWORD),
                    ('th32ParentProcessID', wintypes.DWORD), ('pcPriClassBase', wintypes.LONG),
                    ('dwFlags', wintypes.DWORD), ('szExeFile', wintypes.WCHAR * 260)]
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    for name in ('Process32FirstW', 'Process32NextW'):
        fn = getattr(kernel, name)
        fn.argtypes = [wintypes.HANDLE, ctypes.POINTER(Entry)]
        fn.restype = wintypes.BOOL
    handle = kernel.CreateToolhelp32Snapshot(2, 0)
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        item = Entry()
        item.dwSize = ctypes.sizeof(item)
        ok = kernel.Process32FirstW(handle, ctypes.byref(item))
        if not ok:
            raise ctypes.WinError(ctypes.get_last_error())
        while ok:
            if item.szExeFile.lower() == 'game.exe':
                raise ValueError('請先正常關閉所有 Game.exe 遊戲，再安裝或還原。')
            ok = kernel.Process32NextW(handle, ctypes.byref(item))
        if ctypes.get_last_error() != 18:  # ERROR_NO_MORE_FILES
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        kernel.CloseHandle(handle)


def package():
    with zipfile.ZipFile(PAYLOAD) as archive:
        manifest = json.loads(archive.read('manifest.json'))
        blobs = {name: archive.read(name) for name in manifest['assets']}
    for name, expected in manifest['assets'].items():
        if digest(blobs[name]) != expected:
            raise ValueError('安裝包校驗失敗：' + name)
    if tuple(manifest['installed']) != FILES:
        raise ValueError('安裝包檔案清單不符。')
    return manifest, blobs


def file_hash(path):
    return digest(path.read_bytes()) if path.is_file() else None


def inspect(game, manifest):
    game = Path(game).resolve(strict=True)
    for relative, expected in manifest['baseline'].items():
        if relative == FILES[0]:
            continue
        if file_hash(safe(game, relative)) != expected:
            raise ValueError('遊戲版本不符或檔案已修改：' + relative + '\n請使用支援的原版 3.7 遊戲。')
    current = {name: file_hash(safe(game, name)) for name in FILES}
    if current == manifest['installed']:
        return 'already_installed'
    if current[FILES[0]] != manifest['baseline'][FILES[0]]:
        raise ValueError('腳本不是支援的原版，或已有其他 MOD；為保留修改，已停止。')
    for relative in (*FILES[1:], 'Fonts/fire-ash-zhtw.ttf', 'Fonts/fire-ash-zhtw-LOCAL-ONLY.txt'):
        if safe(game, relative).exists():
            raise ValueError('已有中文化檔案，請先使用原套件還原：' + relative)
    return 'ready'


def font_bytes(manifest, font_dir=None, progress=lambda text: None):
    spec = manifest['font']
    if font_dir:
        data = (Path(font_dir) / Path(FILES[2]).name).read_bytes()
    else:
        progress('下載 Noto 中文字型（約 16 MB），不需安裝至 Windows…')
        request = urllib.request.Request(spec['url'], headers={'User-Agent': 'FireAsh-Extras-Installer/1.0'})
        with urllib.request.urlopen(request, timeout=60) as response:
            if response.geturl().split(':', 1)[0] != 'https':
                raise ValueError('字型下載被轉至非 HTTPS 來源。')
            data = response.read(spec['size'] + 1)
    if len(data) != spec['size'] or digest(data) != manifest['installed'][FILES[2]]:
        raise ValueError('字型校驗失敗；遊戲尚未變更，請檢查網路後重試。')
    return data


def rollback(game, folder, record):
    for relative in reversed(FILES):
        target = safe(game, relative)
        original = record['original'][relative]
        current = file_hash(target)
        if current not in (original, record['installed'][relative]):
            raise ValueError('檔案已被其他程式修改，停止還原：' + relative)
        if original:
            saved = safe(folder, 'original/' + relative)
            if file_hash(saved) != original:
                raise ValueError('備份校驗失敗：' + relative)
            temp = safe(folder, 'restore-' + Path(relative).name)
            shutil.copyfile(saved, temp)
            os.replace(temp, target)
        elif target.exists():
            # Keep removed mod files alongside the original backup, never touch saves.
            removed = safe(folder, 'removed/' + relative)
            removed.parent.mkdir(parents=True, exist_ok=True)
            os.replace(target, removed)


def install(game, font_dir=None, progress=lambda text: None):
    manifest, blobs = package()
    state = inspect(game, manifest)
    if state == 'already_installed':
        return {'status': state, 'message': '相同版本已完整安裝，無需重複套用。'}
    require_closed()
    outputs = {FILES[0]: bsdiff4.patch(safe(game, FILES[0]).read_bytes(), blobs['scripts.bsdiff']),
               FILES[1]: blobs['language.dat'], FILES[3]: blobs['font-license.txt']}
    outputs[FILES[2]] = font_bytes(manifest, font_dir, progress)
    for relative, data in outputs.items():
        if digest(data) != manifest['installed'][relative]:
            raise ValueError('補丁輸出校驗失敗：' + relative)
    # Recheck after downloading. An interrupted previous run must be restored first.
    inspect(game, manifest)
    require_closed()
    backup_root = safe(game, BACKUP)
    pointer = safe(game, BACKUP + '/current.json')
    if pointer.exists():
        previous = safe(backup_root, read_json(pointer)['folder'])
        if read_json(previous / 'manifest.json')['status'] not in ('restored', 'rolled_back'):
            raise ValueError('已有安裝／中斷紀錄，請先按「還原」。')
    folder = safe(backup_root, uuid.uuid4().hex)
    folder.mkdir(parents=True, exist_ok=False)
    record = {'version': manifest['version'], 'game': str(Path(game).resolve()),
              'status': 'prepared', 'installed': manifest['installed'],
              'original': {relative: file_hash(safe(game, relative)) for relative in FILES}}
    progress('備份原始檔案並校驗…')
    for relative in FILES:
        if record['original'][relative]:
            saved = safe(folder, 'original/' + relative)
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(safe(game, relative), saved)
            if file_hash(saved) != record['original'][relative]:
                raise ValueError('備份失敗：' + relative)
        staged = safe(folder, 'staged/' + relative)
        staged.parent.mkdir(parents=True, exist_ok=True)
        staged.write_bytes(outputs[relative])
        if file_hash(staged) != manifest['installed'][relative]:
            raise ValueError('暫存檔校驗失敗：' + relative)
    write_json(folder / 'manifest.json', record)
    write_json(pointer, {'folder': folder.name})
    try:
        require_closed()
        inspect(game, manifest)
        progress('安裝繁中、寶可夢編輯器與遊戲提示／玩法 MOD…')
        for relative in FILES:
            target = safe(game, relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            os.replace(safe(folder, 'staged/' + relative), target)
            if file_hash(target) != manifest['installed'][relative]:
                raise ValueError('安裝校驗失敗：' + relative)
        record['status'] = 'installed'
        write_json(folder / 'manifest.json', record)
    except Exception:
        rollback(game, folder, record)
        record['status'] = 'rolled_back'
        write_json(folder / 'manifest.json', record)
        raise
    return {'status': 'installed', 'backup': str(folder), 'message':
            '安裝完成！開啟遊戲後，在 Language 選擇「繁體中文」。\n存檔保持不變；日後可用本程式還原。'}


def restore(game):
    require_closed()
    pointer = safe(game, BACKUP + '/current.json')
    if not pointer.is_file():
        raise ValueError('找不到本安裝程式的備份，未變更遊戲。')
    folder = safe(safe(game, BACKUP), read_json(pointer)['folder'])
    record = read_json(folder / 'manifest.json')
    if record['game'] != str(Path(game).resolve()):
        raise ValueError('遊戲／備份路徑已改變，請移回原位置後還原。')
    if set(record['original']) != set(FILES) or set(record['installed']) != set(FILES):
        raise ValueError('備份清單不符。')
    if record['status'] in ('restored', 'rolled_back'):
        return {'status': 'restored', 'message': '此備份已還原。'}
    if record['status'] not in ('prepared', 'installed'):
        raise ValueError('未知的備份狀態。')
    # Validate every original before making any write, including crash recovery.
    for relative in FILES:
        original = record['original'][relative]
        if original and file_hash(safe(folder, 'original/' + relative)) != original:
            raise ValueError('備份損壞，未還原：' + relative)
        if file_hash(safe(game, relative)) not in (original, record['installed'][relative]):
            raise ValueError('安裝後又有其他修改，未還原：' + relative)
    rollback(game, folder, record)
    record['status'] = 'restored'
    write_json(folder / 'manifest.json', record)
    return {'status': 'restored', 'backup': str(folder), 'message': '已還原原版遊戲；存檔保持不變。'}


def run(action, game, font_dir=None, progress=lambda text: None):
    game = Path(game).resolve(strict=True)
    if action == 'check':
        manifest, _ = package()
        return {'status': inspect(game, manifest), 'version': manifest['version']}
    lock = safe(game, 'FireAsh-Extras.lock')
    try:
        handle = lock.open('x')
    except FileExistsError:
        raise ValueError('另一個安裝程序正在執行，或上次意外中斷。\n確認沒有安裝程序後，移除 FireAsh-Extras.lock，再按還原。') from None
    try:
        handle.close()
        return install(game, font_dir, progress) if action == 'install' else restore(game)
    finally:
        lock.unlink()


def gui():
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    root = tk.Tk()
    root.title('Fire Ash 3.7 繁中與額外功能安裝程式')
    root.resizable(False, False)
    frame = ttk.Frame(root, padding=22)
    frame.pack(fill='both', expand=True)
    ttk.Label(frame, text='Fire Ash 繁中與額外功能', font=('Microsoft JhengHei UI', 16, 'bold')).pack(anchor='w')
    ttk.Label(frame, text='繁體中文・寶可夢編輯器・地圖與主線提示・戰鬥資訊\n含遇敵間隔、速度命中、等級曲線及野生神獸等現行 MOD。\n首次安裝需連網下載約 16 MB 字型。請先退出遊戲。', justify='left').pack(anchor='w', pady=12)
    location = tk.StringVar()
    entry = ttk.Entry(frame, textvariable=location, width=70)
    entry.pack(fill='x')
    def browse():
        chosen = filedialog.askdirectory(title='選擇包含 Game.exe 的遊戲資料夾')
        if chosen:
            location.set(chosen)
    select = ttk.Button(frame, text='選擇遊戲資料夾…', command=browse)
    select.pack(anchor='w', pady=8)
    beside = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path.cwd()
    if (beside / 'Game.exe').is_file():
        location.set(str(beside))
    status = tk.StringVar(value='備份會留在遊戲資料夾；不修改玩家存檔。')
    ttk.Label(frame, textvariable=status, wraplength=530).pack(anchor='w', pady=8)
    bar = ttk.Progressbar(frame, mode='indeterminate')
    bar.pack(fill='x', pady=5)
    buttons = ttk.Frame(frame)
    buttons.pack(fill='x', pady=8)
    events = queue.Queue()
    busy = False
    def start(action):
        nonlocal busy
        if not location.get():
            browse()
        if not location.get():
            return
        busy = True
        for widget in (entry, select, install_button, restore_button):
            widget.configure(state='disabled')
        bar.start()
        game = location.get()
        def work():
            try:
                result = run(action, game, progress=lambda text: events.put(('progress', text)))
                events.put(('done', result['message']))
            except Exception as error:
                events.put(('error', str(error)))
        threading.Thread(target=work, daemon=True).start()
    install_button = ttk.Button(buttons, text='安裝全部功能', command=lambda: start('install'))
    install_button.pack(side='left')
    restore_button = ttk.Button(buttons, text='還原', command=lambda: start('restore'))
    restore_button.pack(side='left', padx=12)
    def poll():
        nonlocal busy
        while not events.empty():
            kind, message = events.get_nowait()
            status.set(message)
            if kind != 'progress':
                busy = False
                bar.stop()
                for widget in (entry, select, install_button, restore_button):
                    widget.configure(state='normal')
                (messagebox.showerror if kind == 'error' else messagebox.showinfo)('Fire Ash', message)
        root.after(100, poll)
    root.protocol('WM_DELETE_WINDOW', lambda: messagebox.showinfo('Fire Ash', '請等待安裝／還原完成。') if busy else root.destroy())
    poll()
    root.mainloop()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--action', choices=('check', 'install', 'restore'))
    parser.add_argument('--game', type=Path)
    parser.add_argument('--font-dir', type=Path, help='Optional verified offline font folder')
    parser.add_argument('--report', type=Path)
    parser.add_argument('--gui-smoke', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.gui_smoke:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        root.update()
        root.destroy()
        return 0
    if not args.action:
        gui()
        return 0
    if not args.game:
        parser.error('--action requires --game')
    try:
        result = run(args.action, args.game, args.font_dir)
        code = 0
    except Exception as error:
        result, code = {'status': 'error', 'message': str(error)}, 1
    if args.report:
        args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    if sys.stdout:
        print(json.dumps(result, ensure_ascii=False))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
