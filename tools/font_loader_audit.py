"""Read-only checks of the exact installed engine; never loads Game.exe."""
import hashlib
import json
import struct
import sys
from pathlib import Path

import pefile

ENGINE_SHA = "b8994af47f7c911c0550197ccd8566df4638b3b3c147807c33f45b2a06c6d6e0"


def audit_engine(path):
    raw = Path(path).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == ENGINE_SHA, "Different engine: repeat loader investigation"
    pe = pefile.PE(data=raw)
    checks = {
        "ttf_extension": (0x627d6,"817c243874746600"),
        "otf_extension": (0x627e0,"817c24386f746600"),
        "medium_other_slot": (0x32b00,"488d4b50"),
        "default_freetype_modules": (0x89ed0c,"488d056d564700")}
    for name,(rva,expected) in checks.items():
        assert pe.get_data(rva,len(bytes.fromhex(expected))) == bytes.fromhex(expected), name
    base = pe.OPTIONAL_HEADER.ImageBase
    for rva,target in ((0x32961,0x89adcd),(0x3297f,0x89cb75),(0x329d1,0x89cb8a)):
        code = pe.get_data(rva,5)
        assert code[0] == 0xe8 and rva+5+struct.unpack_from("<i",code,1)[0] == target
    # Default FreeType module table includes the CFF driver, not just a diagnostic string.
    assert struct.unpack("<Q",pe.get_data(0xd14390,8))[0] == base+0xd167a0
    assert struct.unpack("<Q",pe.get_data(0xd167a8,8))[0] == base+0xd16790
    assert pe.get_data(0xd16790,4) == b"cff\0"
    assert pe.get_data(0xbe1757,8) == b"Regular\0"
    return {"passed": True,"engine_sha256": ENGINE_SHA,"inspection": "static PE bytes only",
        "extensions": ["ttf","otf"],"scan_callback": "0x140032940",
        "family_lookup": "TTF_FontFaceFamilyName", "non_regular_style": "other font slot",
        "cff_default_driver": True,"font_file_modified": False,"game_executed": False,
        "runtime_load_tested": False,
        "note": "Exact binary supports OTF scanning and registers the CFF driver; actual game launch remains separate QA."}


if __name__ == "__main__":
    print(json.dumps(audit_engine(Path(sys.argv[1])),indent=2))
