"""Export and build a separate Pokémon Essentials 19.1 language pack.

Only build outputs are written; the installed game is always read-only.
"""
import argparse
import csv
import hashlib
import io
import json
import re
import sqlite3
import shutil
import sys
import urllib.request
import unicodedata
import zlib
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT.parents[1]
sys.path.insert(0, str(ARTIFACTS / "downloads/fire-ash-python"))
from rubymarshal.classes import RubyString, UserDef
from rubymarshal.reader import loads
from rubymarshal.writer import Writer, writes as marshal_writes


class LinkedWriter(Writer):
    # rubymarshal 1.2.10 omits bare strings from its object reference table.
    # In mixed legacy/UTF-8 files this can silently redirect later object links.
    def write(self, obj):
        if isinstance(obj, (str, bytes)):
            if self.must_write(obj):
                if isinstance(obj, bytes):
                    self.write_bytes(obj)
                else:
                    self.write_string(obj)
        else:
            super().write(obj)


def writes(obj):
    return marshal_writes(obj, cls=LinkedWriter)

GAME = Path(r"D:\Games\Pokemon Fire Ash\Pokemon Fire Ash 3.7")
DB = ARTIFACTS / "data/fire-ash-work/catalog.sqlite"
DOWNLOADS = ARTIFACTS / "downloads/fire-ash-reference"
REFERENCE_COMMIT = "2bf639e5572812a67d2b94903fdcb9d095f5aeb2"
LABELS = {0: "dialogue", 1: "species", 2: "kinds", 3: "dex", 4: "forms",
          5: "moves", 6: "move-descriptions", 7: "items", 8: "item-plurals",
          9: "item-descriptions", 10: "abilities", 11: "ability-descriptions",
          12: "types", 13: "trainer-types", 14: "trainer-names", 15: "trainer-intro",
          16: "trainer-win", 17: "trainer-lose", 18: "regions", 19: "locations",
          20: "map-points", 21: "map-names", 22: "phone", 23: "battle-quotes",
          24: "ui", 25: "ribbons", 26: "ribbon-descriptions",
          100: "gigantamax-names", 101: "gigantamax-dex"}
LABELS[102] = "supplemental-runtime-ui"
LABELS[103] = "runtime-script-lookups"
LABELS[104] = "runtime-map-lookups"


def text(value):
    return value.decode("utf-8") if isinstance(value, bytes) else str(value)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def json_write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def records(data):
    """Yield source values, never the lookup keys of an OrderedHash."""
    for section, table in enumerate(data):
        if table is None:
            continue
        tables = enumerate(table) if section == 0 else [(None, table)]
        for map_id, obj in tables:
            if obj is None:
                continue
            values = loads(obj._dump())[1] if isinstance(obj, UserDef) else obj
            for index, value in enumerate(values):
                if value:
                    yield section, map_id, index, text(value)


def source_data(game):
    # Default messages include newer entries absent from the shipped english.dat.
    return loads((game / "Data/messages.dat").read_bytes())


def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB)
    db.execute("CREATE TABLE IF NOT EXISTS catalog (section INTEGER, source TEXT, "
               "target TEXT, provenance TEXT, occurrences INTEGER NOT NULL, "
               "PRIMARY KEY(section, source))")
    db.execute("CREATE TABLE IF NOT EXISTS preserved (section INTEGER, source TEXT, "
               "category TEXT NOT NULL, reason TEXT NOT NULL, PRIMARY KEY(section, source))")
    return db


def extract(game):
    data = source_data(game)
    counts = Counter((section, source) for section, _, _, source in records(data))
    db = connect()
    with db:
        for (section, source), count in counts.items():
            db.execute("INSERT INTO catalog VALUES(?,?,NULL,NULL,?) ON CONFLICT(section,source) "
                       "DO UPDATE SET occurrences=excluded.occurrences", (section, source, count))
    out = ROOT / "translation-source/catalog.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="\n") as f:
        for (section, source), count in sorted(counts.items()):
            f.write(json.dumps({"section": section, "category": LABELS.get(section, str(section)),
                                "en": source, "occurrences": count}, ensure_ascii=False) + "\n")
    manifest = {"version_basis": "3.7.1 (bundled changelog)", "game_directory": str(game),
                "files": {name: digest((game / name).read_bytes()) for name in
                          ["Data/messages.dat", "Data/english.dat", "Data/Scripts.rxdata", "Game.ini"]},
                "occurrences": sum(counts.values()), "unique_per_section": len(counts),
                "pokeapi_commit": REFERENCE_COMMIT}
    json_write(ROOT / "source-manifest.json", manifest)
    print(json.dumps(manifest, ensure_ascii=False))


def reference_csv(name):
    path = DOWNLOADS / name
    if not path.exists():
        url = f"https://raw.githubusercontent.com/PokeAPI/pokeapi/{REFERENCE_COMMIT}/data/v2/csv/{name}"
        with urllib.request.urlopen(url, timeout=45) as response:
            payload = response.read()
        # Parse before caching, so an HTML/error response is never treated as data.
        rows = list(csv.DictReader(io.StringIO(payload.decode("utf-8"))))
        if not rows:
            raise ValueError(f"Empty reference: {name}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    return list(csv.DictReader(io.StringIO(path.read_text(encoding="utf-8"))))


def norm(value):
    return " ".join(value.replace("\f", " ").replace("’", "'").split()).casefold()


def names_table(filename, id_field):
    result = defaultdict(dict)
    for row in reference_csv(filename):
        language = row["local_language_id"]
        if language in ("4", "9"):
            result[row[id_field]][language] = row
    return result


def reference(game):
    assert any(r["id"] == "4" and r["identifier"].lower() == "zh-hant"
               for r in reference_csv("languages.csv"))
    db = connect()
    existing = set(db.execute("SELECT section, source FROM catalog"))
    translations = {}
    normalized_sources = defaultdict(list)
    for section, en in existing:
        normalized_sources[(section, norm(en))].append(en)

    def add(section, en, zh, origin):
        if (section, en) not in existing and section in (1, 5, 7, 8, 10, 12):
            candidates = normalized_sources.get((section, norm(en)), [])
            if len(candidates) == 1:
                en = candidates[0]
        if (section, en) in existing and zh and zh != en:
            translations[(section, en)] = (zh, origin)

    for filename, id_field, section in [
        ("pokemon_species_names.csv", "pokemon_species_id", 1),
        ("move_names.csv", "move_id", 5), ("item_names.csv", "item_id", 7),
        ("ability_names.csv", "ability_id", 10), ("type_names.csv", "type_id", 12),
        ("nature_names.csv", "nature_id", 24), ("region_names.csv", "region_id", 18),
        ("location_names.csv", "location_id", 19), ("location_names.csv", "location_id", 20),
        ("location_names.csv", "location_id", 21),
    ]:
        for row in names_table(filename, id_field).values():
            if "4" not in row or "9" not in row:
                continue
            en, zh = row["9"]["name"], row["4"]["name"]
            add(section, en, zh, filename)
            if section == 1:
                # Essentials stores the genus without its final "Pokémon" word.
                en_genus = row["9"]["genus"].removesuffix(" Pokémon")
                zh_genus = row["4"]["genus"].removesuffix("寶可夢")
                add(2, en_genus, zh_genus, filename)

    for row in names_table("pokemon_form_names.csv", "pokemon_form_id").values():
        if "4" in row and "9" in row:
            for field in ("form_name", "pokemon_name"):
                en, zh = row["9"][field], row["4"][field]
                if en and zh:
                    add(4, en, zh, "pokemon_form_names.csv")

    for filename, id_field, version_field, language_field, text_field, section in [
        ("move_flavor_text.csv", "move_id", "version_group_id", "language_id", "flavor_text", 6),
        ("item_flavor_text.csv", "item_id", "version_group_id", "language_id", "flavor_text", 9),
        ("ability_flavor_text.csv", "ability_id", "version_group_id", "language_id", "flavor_text", 11),
        ("pokemon_species_flavor_text.csv", "species_id", "version_id", "language_id", "flavor_text", 3),
    ]:
        grouped = defaultdict(dict)
        for row in reference_csv(filename):
            if row[language_field] in ("4", "9"):
                grouped[(row[id_field], int(row[version_field]))][row[language_field]] = row[text_field]
        match = {}
        for (_, version), pair in sorted(grouped.items(), key=lambda x: x[0][1]):
            if "4" in pair and "9" in pair:
                match[norm(pair["9"])] = "".join(pair["4"].split())
        for sec, en in existing:
            if sec == section and norm(en) in match:
                add(sec, en, match[norm(en)], filename + ":exact-english-match")

    # Chinese has no separate plural form. Use the paired singular item slot.
    data = source_data(game)
    for i, plural in enumerate(data[8]):
        if not plural or i >= len(data[7]) or not data[7][i]:
            continue
        singular = text(data[7][i])
        match = translations.get((7, singular))
        if match:
            add(8, text(plural), match[0], "paired-item-singular")
    out = ROOT / "translations/reference.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="\n") as f:
        for (section, en), (zh, origin) in sorted(translations.items()):
            f.write(json.dumps({"section": section, "en": en, "zh-TW": zh,
                                "source": "PokeAPI/" + origin}, ensure_ascii=False) + "\n")
    print("Reference translations:", len(translations))


# Argument-bearing codes (e.g. \v[1], \se[...]) must remain byte-for-byte intact.
# Formatting codes are also retained; punctuation and ordinary words are free to change.
TOKENS = re.compile(r"#\{[^{}]*\}|\{\d+(?:[^{}]*)\}|\\(?:[A-Za-z]+\[[^\]]*\]|PN|PM|PG|CN|TN|TP|TE|[A-Za-z.!|^<>$])|</?[A-Za-z][A-Za-z0-9_-]*(?:=[^>]*|\s+[A-Za-z_][A-Za-z0-9_-]*=[^>]*)?\s*/?>|%\d*\$?[sdiuf]|[\x01]", re.I)


def message_csv_fields(value):
    """Match the game's pbCsvField!: backslash escapes only in quoted fields."""
    fields = []
    while value:
        value = value.lstrip()
        if value.startswith('"'):
            result = []
            escaped = False
            pos = 1
            while pos < len(value):
                char = value[pos]
                pos += 1
                if char == '"' and not escaped:
                    break
                if char == "\\" and not escaped:
                    escaped = True
                else:
                    result.append(char)
                    escaped = False
            value = value[pos:].lstrip()
            if value and not value.startswith(","):
                raise ValueError("Invalid quoted message CSV field")
            value = value[1:] if value.startswith(",") else ""
            fields.append("".join(result))
        else:
            field, _, value = value.partition(",")
            fields.append(field.rstrip())
    return fields


def message_choice_blocks(text_value):
    end = 0
    for match in re.finditer(r"\\ch\[", text_value, re.I):
        if match.start() < end:
            continue
        pos, depth = match.end(), 1
        quoted = escaped = False
        field_start = True
        while pos < len(text_value) and depth:
            char = text_value[pos]
            pos += 1
            if quoted:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    quoted = False
            elif char == '"' and field_start:
                quoted, field_start = True, False
            elif char == "[":
                depth += 1
                field_start = False
            elif char == "]":
                depth -= 1
            elif char == ",":
                field_start = True
            elif not char.isspace():
                field_start = False
        if depth == 0:
            end = pos
            yield match.start(), pos, match.group(), text_value[match.end():pos - 1]


def analyze_message(value):
    controls, visible = [], []
    hide_control = lambda match: "\n" if match.group().lower() == r"\n" else " "
    cursor = 0
    for start, end, prefix, payload in message_choice_blocks(value):
        before = value[cursor:start]
        controls.extend(TOKENS.findall(before))
        visible.append(TOKENS.sub(hide_control, before))
        fields = message_csv_fields(payload)
        if len(fields) >= 2:
            labels = fields[2:]
            label_controls = tuple(frozenset(Counter(TOKENS.findall(label)).items()) for label in labels)
            controls.append((prefix, fields[0], fields[1], len(labels), label_controls))
            controls.extend(TOKENS.findall(payload))
            visible.extend(TOKENS.sub(hide_control, label) for label in labels)
        else:
            controls.extend(TOKENS.findall(value[start:end]))
        cursor = end
    controls.extend(TOKENS.findall(value[cursor:]))
    visible.append(TOKENS.sub(hide_control, value[cursor:]))
    return Counter(controls), " ".join(visible)


def validate_pair(en, zh):
    if not isinstance(zh, str) or not zh.strip():
        raise ValueError(f"Empty translation: {en!r}")
    if analyze_message(en)[0] != analyze_message(zh)[0]:
        raise ValueError(f"Changed control codes: {en!r} -> {zh!r}")


def parse_manual_batch(raw_source, manual, existing):
    if digest(raw_source) != manual["source_sha256"]:
        raise ValueError("Translation batch source hash changed")
    sources = [json.loads(line) for line in raw_source.decode("utf-8").splitlines()]
    targets = manual["zh-TW"]
    if not isinstance(targets, list) or len(sources) != len(targets):
        raise ValueError("Translation batch source/target count differs")
    result = {}
    for row, target in zip(sources, targets):
        key = (row["section"], row["en"])
        if key not in existing:
            raise ValueError(f"Translation batch contains an unknown source: {key}")
        validate_pair(row["en"], target)
        result[key] = (target, "Codex/manual-batch")
    return result


def translate_teleport(en, translations, terms):
    match = re.fullmatch(r"(\\[br])?(My )?(.+?) can Teleport you\.\s*(\\ch\[.*\])", en, re.S)
    if not match:
        return None
    speaker = terms["speaker_aliases"].get(match[3])
    if speaker is None:
        species = translations.get((1, match[3]))
        speaker = species[0] if species else match[3] if match[3] in terms["retained_speakers"] else None
    blocks = list(message_choice_blocks(match[4]))
    if speaker is None or len(blocks) != 1 or blocks[0][:2] != (0, len(match[4])):
        return None
    fields = message_csv_fields(blocks[0][3])
    if len(fields) < 3 or any(label not in terms["destinations"] for label in fields[2:]):
        return None
    labels = [terms["destinations"][label] for label in fields[2:]]
    target = ((match[1] or "") + ("我的" if match[2] else "") + speaker
              + "可以用瞬間移動送你前往各地。" + blocks[0][2]
              + ",".join(fields[:2] + labels) + "]")
    validate_pair(en, target)
    return target


def import_translations(db, game=GAME):
    translations = {}
    explicit_preserved = {}
    reference_path = ROOT / "translations/reference.jsonl"
    if reference_path.exists():
        for line in reference_path.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            translations[(row["section"], row["en"])] = (row["zh-TW"], row["source"])
    manual_paths = [ROOT / "translations" / name for name in
                    ["manual.json", "manual-names.json", "manual-story.json", "runtime-ui.json"]]
    manual_paths += sorted((ROOT / "translations/batches").glob("*.json"))
    for path in manual_paths:
        filename = path.name
        manual = json.loads(path.read_text(encoding="utf-8"))
        for section, entries in manual.get("preserved_sources", {}).items():
            for en, category in entries.items():
                explicit_preserved[(int(section), en)] = (
                    category, manual.get("retained_terms", {}).get(en,
                        manual.get("retained_terms", {}).get(analyze_message(en)[1].strip(),
                                                           "已核對並指定保留原文的識別名稱。")))
        if "source_sha256" in manual:
            source_path = ROOT / "translation-source/batches" / (path.stem + ".jsonl")
            translations.update(parse_manual_batch(source_path.read_bytes(), manual,
                                                   set(db.execute("SELECT section,source FROM catalog"))))
            continue
        origin = "Codex/names-draft" if filename == "manual-names.json" else "Codex/manual"
        for section, en in db.execute("SELECT section, source FROM catalog"):
            category = manual.get(str(section), {})
            if en in category:
                translations[(section, en)] = (category[en], origin)
            elif section != 14 and en in manual.get("all", {}) and (section, en) not in translations:
                translations[(section, en)] = (manual["all"][en], origin)
        for section, entries in manual.items():
            if section.isdigit():
                for en, zh in entries.items():
                    translations[(int(section), en)] = (zh, origin)
    # Canonical names outrank generic UI words: Psychic is a move and a type.
    for line in reference_path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row["section"] in (1, 4, 5, 7, 8, 10, 12, 18, 19, 20, 21):
            translations[(row["section"], row["en"])] = (row["zh-TW"], row["source"])
    original = source_data(game)
    existing = set(db.execute("SELECT section, source FROM catalog"))
    for i, plural in enumerate(original[8]):
        if not plural or i >= len(original[7]) or not original[7][i]:
            continue
        single = translations.get((7, text(original[7][i])))
        if single and (8, text(plural)) not in translations:
            translations[(8, text(plural))] = (single[0], "paired-item-singular")
    for section, en in existing:
        if section == 9 and (section, en) not in translations and (6, en) in translations:
            translations[(section, en)] = (translations[(6, en)][0], "identical-tm-move-description")
        if section == 14 and (1, en) in translations and (section, en) not in translations:
            translations[(section, en)] = (translations[(1, en)][0], "canonical-species-as-name")
        if section == 100 and en.startswith("Gigantamax "):
            species = translations.get((1, en.removeprefix("Gigantamax ")))
            if species:
                translations[(100, en)] = ("超極巨化" + species[0], "composed-species-name")
        if section in (0, 19, 20, 21) and (section, en) not in translations:
            for peer in (19, 20, 21):
                place = translations.get((peer, en))
                if place:
                    translations[(section, en)] = (place[0], "shared-place-name")
                    break
    for section, en in existing:
        if section != 4 or (section, en) in translations:
            continue
        target = None
        if en.startswith("Mega "):
            base = en.removeprefix("Mega ")
            suffix = base[-2:] if base.endswith((" X", " Y")) else ""
            species = translations.get((1, base[:-2] if suffix else base))
            if species:
                target = "超級" + species[0] + suffix
        elif en.startswith("Type: ") or en.endswith(" Type"):
            base = en.removeprefix("Type: ") if en.startswith("Type: ") else en.removesuffix(" Type")
            kind = translations.get((12, base))
            if kind:
                target = ("屬性：" + kind[0]) if en.startswith("Type: ") else kind[0] + "屬性"
        elif (1, en) in translations:
            target = translations[(1, en)][0]
        elif "," in en:
            parts = [translations.get((4, part)) for part in en.split(",")]
            if all(parts):
                target = ",".join(part[0] for part in parts)
        if target:
            translations[(section, en)] = (target, "composed-canonical-name")
    signature_prefixes = {"Neo Champion": "新冠軍", "Anni": "週年慶", "Arc Suit": "阿爾宙斯套裝",
                          "Sygna Suit": "美極套裝", "SS": "美極套裝", "Dojo": "武館制服"}
    for section, en in existing:
        if section != 6 or (section, en) in translations:
            continue
        match = re.fullmatch(r"(.+)'s signature move\.", en)
        if not match:
            continue
        owner = match[1]
        prefix = ""
        for english, chinese in signature_prefixes.items():
            if owner.startswith(english + " "):
                prefix, owner = chinese, owner[len(english) + 1:]
                break
        person = translations.get((14, owner))
        if person:
            translations[(section, en)] = (prefix + person[0] + "的專屬招式。", "composed-signature-description")
    # Reuse reviewed sentences that differ only in spacing or speaker color.
    # No partial word substitution or automatic translation is performed here.
    equivalent = defaultdict(set)
    for (section, en), (zh, _) in translations.items():
        en_color = re.match(r"^\\[br]", en)
        zh_color = re.match(r"^\\[br]", zh)
        if en_color and zh_color and en_color.group() == zh_color.group():
            en, zh = en[2:], zh[2:]
        equivalent[(section, re.sub(r" {2,}", " ", en).strip(" "))].add(zh)
    for section, en in existing:
        if (section, en) in translations:
            continue
        color = en[:2] if re.match(r"^\\[br]", en) else ""
        base = en[2:] if color else en
        key = re.sub(r" {2,}", " ", base).strip(" ")
        alternatives = equivalent.get((section, key), set())
        if len(alternatives) == 1:
            translations[(section, en)] = (color + next(iter(alternatives)), "equivalent-reviewed-sentence")
        elif section == 0:
            punctuation = base[-1:] if base.endswith(("!", ".")) else ""
            name = base[:-1] if punctuation else base
            canonical = translations.get((1, name)) or translations.get((14, name))
            if canonical:
                ending = {"!": "！", ".": "。", "": ""}[punctuation]
                translations[(section, en)] = (color + canonical[0] + ending, "canonical-name-caption")
    teleport_terms = json.loads((ROOT / "translations/teleport-template.json").read_text(encoding="utf-8"))
    for section, en in existing:
        if section == 0 and (section, en) not in translations:
            target = translate_teleport(en, translations, teleport_terms)
            if target:
                translations[(section, en)] = (target, "reviewed-teleport-template")
    runtime_identifiers = json.loads((ROOT / "translations/runtime-identifiers.json").read_text(encoding="utf-8"))
    reserved_keys = {(int(section), en) for section, values in runtime_identifiers.items()
                     if section.isdigit() for en in values}
    for section, en in reserved_keys:
        translations[(section, en)] = (en, "runtime-resource-identifier")
    for key in explicit_preserved:
        if key not in existing:
            raise ValueError(f"Unknown preserved source: {key}")
        if key in translations and translations[key][0] != key[1]:
            raise ValueError(f"Preservation conflicts with translation: {key}")
        translations[key] = (key[1], "reviewed-preservation")
    with db:
        db.execute("UPDATE catalog SET target=NULL, provenance=NULL")
        for (section, en), (zh, origin) in translations.items():
            validate_pair(en, zh)
            if zh == en:
                continue
            db.execute("UPDATE catalog SET target=?, provenance=? WHERE section=? AND source=?",
                       (zh, origin, section, en))
        db.execute("DELETE FROM preserved")
        for section, source in db.execute("SELECT section,source FROM catalog WHERE target IS NULL").fetchall():
            category = reason = None
            stripped = analyze_message(source)[1].strip()
            if (section, source) in reserved_keys:
                category, reason = "runtime-resource-identifier", runtime_identifiers["reason"]
            elif (section, source) in explicit_preserved:
                category, reason = explicit_preserved[(section, source)]
            elif source.startswith(("Graphics/", "Audio/", "Data/")):
                category, reason = "resource-path", "程式查找用的資源路徑，翻譯會導致找不到檔案。"
            elif (section, source) in translations and translations[(section, source)][0] == source:
                category, reason = "standard-abbreviation", "已明確指定保留的標準縮寫或識別符號。"
            elif not stripped or not re.search(r"[A-Za-z\u3400-\u9fff]", stripped):
                category, reason = "formatting", "空白、標點、數字或純格式／替換碼，保留原樣避免改變顯示邏輯。"
            elif section == 4 and re.fullmatch(r"[A-Z!?]", source):
                category, reason = "unown-symbol", "未知圖騰的字母／標點型態識別，不是待翻譯單字。"
            elif section == 5 and source == "UUDDLRLRBAS":
                category, reason = "button-sequence", "招式名本身為按鍵代碼，保留原始按鍵名稱與順序。"
            elif section == 14:
                category, reason = "trainer-name-original", "尚未建立已核對的繁中對照或身分有歧義的訓練家人名，保留原拼字以便與原版交叉辨識。"
            if category:
                db.execute("INSERT INTO preserved VALUES(?,?,?,?)", (section, source, category, reason))
    return translations


def make_batch(section, limit, name, menu_only=False):
    if not re.fullmatch(r"\d{3}-[a-z0-9-]+", name or ""):
        raise ValueError("Batch name must be NNN-lowercase-topic")
    if limit < 1:
        raise ValueError("Batch limit must be positive")
    path = ROOT / "translation-source/batches" / (name + ".jsonl")
    if not path.exists():
        db = connect()
        import_translations(db)
        selection = "AND lower(c.source) LIKE ? " if menu_only else ""
        params = (section, "%\\ch[%", limit) if menu_only else (section, limit)
        rows = list(db.execute("SELECT c.section,c.source FROM catalog c LEFT JOIN preserved p "
                               "ON c.section=p.section AND c.source=p.source "
                               "WHERE c.section=? AND c.target IS NULL AND p.source IS NULL "
                               + selection + "ORDER BY c.source LIMIT ?", params))
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = "".join(json.dumps({"section": sec, "en": en}, ensure_ascii=False) + "\n" for sec, en in rows)
        path.write_text(payload, encoding="utf-8", newline="\n")
    raw = path.read_bytes()
    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines()]
    print("source_sha256:", digest(raw), "count:", len(rows))
    for i, row in enumerate(rows, 1):
        print(i, row["en"])


def translate_data(data, translations):
    changed = 0
    for section, table in enumerate(data):
        if table is None:
            continue
        for obj in table if section == 0 else [table]:
            if obj is None:
                continue
            pair = loads(obj._dump()) if isinstance(obj, UserDef) else None
            values = pair[1] if pair is not None else obj
            for i, value in enumerate(values):
                if value:
                    target = translations.get((section, text(value)))
                    if target:
                        # Ruby 3 needs explicit UTF-8 metadata for interpolation.
                        values[i] = RubyString(target[0], {"E": True})
                        changed += target[0] != text(value)
            if pair is not None:
                obj._load(writes(pair))
    return changed


def runtime_ui_sources(game=GAME):
    scripts = {text(row[1]): zlib.decompress(row[2]).decode("utf-8")
               for row in loads((game / "Data/Scripts.rxdata").read_bytes())}
    code = scripts["Sygna Buffs"]
    literal = r'"(?:\\.|[^"\\])*"'
    pairs = re.finditer(r'SygnaBuff\.new\(\s*(' + literal + r')\s*,\s*(nil|' + literal + r')', code)
    sources = {json.loads(value) for match in pairs for value in match.groups()
               if value != "nil" and "#{" not in value}
    for value in list(sources):
        if re.search(r" Lv\. \d+$", value):
            sources.update(re.sub(r"\d+$", str(level), value) for level in (1, 2, 3))
    sources.update(json.loads(value) for value in re.findall(r'"(?:HP|PP)[23]"\s*=>\s*(' + literal + r')', code))
    sources.update({"GC Credits", "Status Recovery", "Full Healing",
                    "Nurse Joy removes status conditions from your team. Costs 3 energy. Sync Challenge only.",
                    "Nurse Joy heals your team properly. Unable to equip other buffs. Sync Challenge only."})
    for name in ("UI_ClubRecords", "UI_PracticeRecords"):
        sources.update(json.loads(value) for value in re.findall(r'region\s*=\s*(' + literal + r')', scripts[name])
                       if json.loads(value).strip())
    return sorted(sources)


def export_runtime_sources(game=GAME, verbose=True):
    rows = [{"section": 102, "en": value, "storage": "Scripts.rxdata/display-only"}
            for value in runtime_ui_sources(game)]
    path = ROOT / "translation-source/runtime-ui.jsonl"
    payload = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
    path.write_text(payload, encoding="utf-8", newline="\n")
    if verbose:
        print("Runtime UI sources:", len(rows), "SHA256:", digest(payload.encode("utf-8")))
        for i, row in enumerate(rows, 1):
            print(i, repr(row["en"]))
    return [row["en"] for row in rows]


def prepare_runtime_catalog(db, game=GAME):
    sources = export_runtime_sources(game, verbose=False)
    targets = json.loads((ROOT / "translations/runtime-ui.json").read_text(encoding="utf-8"))["102"]
    if set(targets) != set(sources):
        raise ValueError(f"Supplemental runtime UI differs: missing={set(sources)-set(targets)}, unknown={set(targets)-set(sources)}")
    with db:
        db.executemany("INSERT OR IGNORE INTO catalog(section,source,occurrences) VALUES(102,?,0)",
                       ((source,) for source in sources))
    return targets


def prepare_missing_catalog(db, game):
    from runtime_catalog import collect
    rows = collect(game)
    expected = {(row["section"], row["en"]) for row in rows}
    committed = [json.loads(line) for path in sorted((ROOT / "translation-source/batches").glob("*-runtime-missing.jsonl"))
                 for line in path.read_text(encoding="utf-8").splitlines()]
    if rows != committed:
        raise ValueError("Native runtime source inventory changed; review and translate new batches")
    with db:
        db.executemany("INSERT OR IGNORE INTO catalog(section,source,occurrences) VALUES(?,?,0)", sorted(expected))
    return rows


def append_runtime_translations(data, translations, rows):
    """Append missing lookup keys; preserve every original key/value position."""
    counts = {103: 0, 104: 0}
    for section, table in ((103, data[24]), (104, data[0][0])):
        keys, values = loads(table._dump())
        for row in rows:
            if row["section"] != section:
                continue
            en = row["en"]
            if en in keys:
                raise ValueError(f"Supplemental key already exists: {section}: {en!r}")
            zh, _ = translations[(section, en)]
            validate_pair(en, zh)
            keys.append(RubyString(en, {"E": True}))
            values.append(RubyString(zh, {"E": True}))
            counts[section] += 1
        table._load(writes([keys, values]))
    return counts


def patch_text_layout(code):
    marker = "    if hadspace && !isspace"
    if code.count(marker) != 2:
        raise ValueError("Expected both original DrawText word-boundary checks")
    newline = "\r\n" if "\r\n" in code else "\n"
    replacement = newline.join([
        "    if defined?(FireAshZHTW) && FireAshZHTW.cjk_boundary?(",
        "         position > 0 ? textchars[position - 1] : nil, textchars[position])",
        "      lastword[0]=characters.length",
        "      lastword[1]=x",
        "      hadspace=false",
        "      hadnonspace=true",
        "    elsif hadspace && !isspace"])
    return code.replace(marker, replacement)


def patch_text_effects(code):
    newline = "\r\n" if "\r\n" in code else "\n"
    shadow_calls = newline.join([
        "      bitmap.font.color=shadowColor",
        "      bitmap.draw_text(textx+2,texty,width+2,height,text)",
        "      bitmap.draw_text(textx,texty+2,width+2,height,text)",
        "      bitmap.draw_text(textx+2,texty+2,width+2,height,text)"])
    changes = [
        ("pbDrawShadowText", "  y += 4",
         "  y += FireAshZHTW.row_text_offset(bitmap, height)"),
        ("pbDrawShadowText", "if shadowColor && shadowColor.alpha>0",
         "if shadowColor && shadowColor.alpha>0 && !FireAshZHTW.active?"),
        ("drawSingleFormattedChar", "if ch[9] # shadow",
         "if ch[9] && (!FireAshZHTW.active? || (ch[16]&3)!=0) # keep explicit outlines"),
        ("renderLineBrokenChunksWithShadow", shadow_calls,
         "      unless FireAshZHTW.active?" + newline +
         newline.join("  " + line for line in shadow_calls.split(newline)) + newline + "      end")]
    for name, before, after in changes:
        method = re.search(r"^def " + name + r"\b.*?^end\b", code, re.M | re.S)
        if not method or method[0].count(before) != 1:
            raise ValueError(f"Unexpected original text effect method: {name}")
        code = code[:method.start()] + method[0].replace(before, after) + code[method.end():]
    return code


def ruby_string(value):
    # JSON's quoted-string subset is valid Ruby; suppress Ruby interpolation.
    return re.sub(r"#(?=[{@$])", r"\\#", json.dumps(value, ensure_ascii=False))


def runtime_support_code(targets):
    dictionary = ",\n".join("    " + ruby_string(en) + " => " + ruby_string(zh)
                            for en, zh in sorted(targets.items()))
    return ("# encoding: UTF-8\nmodule FireAshZHTW\n  RUNTIME_TEXT = {\n" + dictionary
            + "\n  }.freeze\nend\n" + (ROOT / "tools/runtime_support.rb").read_text(encoding="utf-8")).encode("utf-8")


def patch_runtime_text(code, name, ui_keys):
    changes = []
    literal = r'"(?:\\.|[^"\\])*"'

    def replace(match):
        raw = match.group(1)
        expressions = re.findall(r"(?<!\\)#\{([^{}]+)\}", raw)
        if not expressions:
            return match.group()
        key = json.loads(raw)
        if key not in ui_keys:
            raise ValueError(f"Interpolated UI key is not in the original language table: {name}: {key}")
        bindings = ", ".join(ruby_string("#{" + expr + "}") + " => (" + expr + ")"
                             for expr in dict.fromkeys(expressions))
        changes.append({"script": name, "kind": "interpolation-before-lookup", "key": key,
                        "bindings": expressions})
        return "FireAshZHTW.intl(" + ruby_string(key) + ", {" + bindings + "}"

    code = re.sub(r'_INTL\(\s*(' + literal + r')', replace, code)
    replacements = []
    if name == "Sygna Buffs":
        replacements = [
            ('_INTL("{1} - {2}", name, description)', '_INTL("{1} - {2}", display_name, display_description)'),
            ('choices = "#{choices},#{b.name} - #{b.cost} GC Credits"',
             'choices = "#{choices},#{b.display_name} - #{b.cost} #{FireAshZHTW.text("GC Credits")}"'),
            ('buffs = "#{buffs},#{b.name}"', 'buffs = "#{buffs},#{b.display_name}"')]
        for verb in ("BOUGHT", "EQUIPPED", "UNEQUIPPED"):
            replacements.append((f'_INTL("{verb} {{1}}.", buff.name)',
                                 f'_INTL("{verb} {{1}}.", buff.display_name)'))
    if name in ("UI_ClubRecords", "UI_PracticeRecords"):
        kind = "Club" if name == "UI_ClubRecords" else "Practice"
        replacements.append((f'_INTL("{{1}}{kind} Completion No.{{2}}{{3}}", region,',
                             f'_INTL("{{1}}{kind} Completion No.{{2}}{{3}}", FireAshZHTW.text(region),'))
    if name == "Interpreter_Commands":
        replacements.append((
            'command = pbShowCommands(nil, @list[@index].parameters[0], @list[@index].parameters[1])',
            'choices = @list[@index].parameters[0]\n    choices = choices.map { |choice| _MAPINTL($game_map.map_id, choice) } if FireAshZHTW.active?\n'
            '    command = pbShowCommands(nil, choices, @list[@index].parameters[1])'))
    if name == "SpriteWindow_text":
        newline = "\r\n" if "\r\n" in code else "\n"
        # A larger backing bitmap still gets clipped by the fixed contents src_rect.
        # Fit text inside each 32px row instead; do not shift icons above their row.
        replacements.append((
            '    else' + newline + '      if @letterbyletter' + newline + '        @fmtchars = []',
            '    else' + newline +
            '      dialog_y_offset = FireAshZHTW.row_text_offset(self.contents, 32)' + newline +
            '      if @letterbyletter' + newline + '        @fmtchars = []'))
        for following in ('          if !ch[5]', '          @textchars.push'):
            replacements.append((
                '          ch[2] += 4' + newline + following,
                '          ch[2] += ch[5] ? [dialog_y_offset, 0].max : dialog_y_offset' + newline + following))
        replacements.extend([
            ('    self.height=dims[1] - 6',
             '    self.height=dims[1] - (FireAshZHTW.active? ? 0 : 6)'),
            ('         self.contents,rect.x,rect.y+4,rect.width,rect.height,',
             '         self.contents,rect.x,rect.y,rect.width,rect.height,'),
            ('         @commands[index],rect.height,true,true)' + newline + '      drawFormattedChars(self.contents,chars)',
             '         @commands[index],rect.height,true,true)' + newline +
             '      offset = FireAshZHTW.row_text_offset(self.contents, rect.height)' + newline +
             '      chars.each { |ch| ch[2] += ch[5] ? [offset, 0].max : offset }' + newline +
             '      drawFormattedChars(self.contents,chars)')])
    direct = {
        "Minigame_VoltorbFlip": [("pbConfirmMessage", "You haven't found any Coins! Are you sure you want to quit?")],
        "EditorScreens": [("pbConfirmMessageSerious", f"Delete this {kind}?") for kind in
                          ("trainer type", "trainer battle", "item", "species")],
        "EditorScreens_SpritePositioning": [("pbMessage", "This species has its own shadow sprite in Graphics/Pokemon/Shadow/. The shadow size metric cannot be edited.")],
        "Debug_MenuSpriteRenamer": [("pbConfirmMessage", value) for value in (
            "Check for Pokémon/item/trainer files in their old folders that need renaming and moving?",
            "Rename all trainer charsets? This will also edit map data to change events' charsets accordingly.")],
    }
    for function, value in direct.get(name, []):
        literal_value = ruby_string(value)
        replacements.append((f"{function}({literal_value})", f"{function}(_INTL({literal_value}))"))
    if name == "UI_EnemyBuffs":
        for label in ("Attack Buff", "Defense Buff", "Sp. Attack Buff", "Sp. Defense Buff", "Speed Buff",
                      "Accuracy Buff", "Evasion Buff", "Status Immunity", "Interference Immunity", "Vigilance"):
            replacements.append((f'when "{label}"', f'when _INTL("{label}")'))
    if name == "UI_ShowChallengeTeam":
        replacements.append(('_INTL(header),Graphics.width/2-5*header.length,-6,0,BASECOLOR,SHADOWCOLOR',
                             '_INTL(header),FireAshZHTW.active? ? Graphics.width/2 : Graphics.width/2-5*header.length,'
                             '-6,FireAshZHTW.active? ? 2 : 0,BASECOLOR,SHADOWCOLOR'))
    for previous, revised in replacements:
        if code.count(previous) != 1:
            raise ValueError(f"Unexpected display-only call site: {name}: {previous}")
        code = code.replace(previous, revised)
        changes.append({"script": name, "kind": "display-only", "before": previous, "after": revised})
    return code, changes


def font_config(font_source="pixel"):
    if font_source not in ("pixel", "jhenghei", "noto"):
        raise ValueError(f"Unknown font source: {font_source}")
    filename = "font-source.json" if font_source == "pixel" else f"font-source-{font_source}.json"
    return json.loads((ROOT / filename).read_text(encoding="utf-8"))


def staged_font_path(font_source):
    assert font_source in ("pixel", "jhenghei", "noto")
    return ARTIFACTS / "data/fire-ash-work/fonts" / (
        "fire-ash-zhtw.otf" if font_source == "noto" else "fire-ash-zhtw.ttf")


def font_support_code(font_source="pixel"):
    code = (ROOT / "tools/font_support.rb").read_text(encoding="utf-8")
    marker = '  FONT = "Fusion Pixel 12px Mono zh-TW"'
    assert code.count(marker) == 1, "Unexpected font hook template"
    config = font_config(font_source)
    code = code.replace(marker, "  FONT = " + ruby_string(config["family"]))
    if font_source == "noto":
        family, legacy = ruby_string(config["family"]), ruby_string(config["legacy_family"])
        code = code.replace("  FONT = " + family,
                            f"  FONT = Font.exist?({family}) ? {family} : {legacy}")
        guard = ('  def self.ensure_loaded!\n    return unless active?\n'
                 '    raise RuntimeError, "Noto font not loaded: Fonts/fire-ash-zhtw.otf. '
                 'Restore the trial backup before continuing." unless Font.exist?(FONT)\n  end\n\n')
        code = code.replace("  def self.with_text_font",guard + "  def self.with_text_font")
        code = code.replace("    font = bitmap.font\n","    ensure_loaded!\n    font = bitmap.font\n")
        code = code.replace("    if FireAshZHTW.active?\n", "    if FireAshZHTW.active?\n      FireAshZHTW.ensure_loaded!\n")
    return code.encode("utf-8")


def audit_full_key(game):
    uses = []
    for _, name, compressed in loads((game / "Data/Scripts.rxdata").read_bytes()):
        code = zlib.decompress(compressed).decode("utf-8")
        for line_number, line in enumerate(code.splitlines(), 1):
            if re.search(r'''["']Full["']''', line):
                uses.append({"script": text(name), "line": line_number, "code": line.strip()})
    assert len(uses) == 1 and uses[0]["script"] == "UI_Options", "Full gained another context; review before translating"
    assert '_INTL("Screen Size")' in uses[0]["code"] and '_INTL("Full")' in uses[0]["code"]
    json_write(ROOT / "full-key-usage.json", {"original_scripts_sha256": digest(
        (game / "Data/Scripts.rxdata").read_bytes()), "exact_literal_uses": uses,
        "translation": "全螢幕", "decision": "原版完整 Full 字串僅用於畫面大小；其他容量訊息使用不同鍵。"})


def build_scripts(game, runtime_targets, font_source="pixel"):
    scripts = loads((game / "Data/Scripts.rxdata").read_bytes())
    settings = [row for row in scripts if text(row[1]) == "Settings"]
    assert len(settings) == 1, "Cannot uniquely identify Settings"
    row = settings[0]
    code = zlib.decompress(row[2]).decode("utf-8")
    match = re.search(r"(LANGUAGES\s*=\s*\[)(.*?)(\r?\n\s*\])", code, re.S)
    assert match and "traditional_chinese.dat" not in match.group(), "Unexpected language setup"
    # Append; existing saved language indices keep their original meaning.
    newline = "\r\n" if "\r\n" in code else "\n"
    addition = newline + '    ["繁體中文", "traditional_chinese.dat"],'
    patched = "# encoding: UTF-8" + newline + code[:match.end(2)] + addition + code[match.end(2):]
    row[2] = zlib.compress(patched.encode("utf-8"))
    draw_scripts = [row for row in scripts if text(row[1]) == "DrawText"]
    assert len(draw_scripts) == 1, "Cannot uniquely identify text layout script"
    row = draw_scripts[0]
    row[2] = zlib.compress(patch_text_effects(patch_text_layout(
        zlib.decompress(row[2]).decode("utf-8"))).encode("utf-8"))
    ui_keys = {en for section, _, _, en in records(source_data(game)) if section == 24}
    runtime_patches = []
    for row in scripts:
        code, changes = patch_runtime_text(zlib.decompress(row[2]).decode("utf-8"), text(row[1]), ui_keys)
        if changes:
            row[2] = zlib.compress(code.encode("utf-8"))
            runtime_patches.extend(changes)
    assert sum(change["kind"] == "interpolation-before-lookup" for change in runtime_patches) == 11, "Unexpected interpolation call count"
    font_code = font_support_code(font_source)
    main_index = next(i for i, row in enumerate(scripts) if text(row[1]) == "Main")
    scripts.insert(main_index, [max(row[0] for row in scripts) + 1,
                               b"FireAsh_ZHTW_Font", zlib.compress(font_code)])
    scripts.insert(main_index + 1, [max(row[0] for row in scripts) + 1,
                                   b"FireAsh_ZHTW_Runtime", zlib.compress(runtime_support_code(runtime_targets))])
    output = writes(scripts)
    restored = loads(output)
    assert all(a[0] == b[0] and text(a[1]) == text(b[1]) and a[2] == b[2]
               for a, b in zip(scripts, restored)), "Script archive changed on serialization"
    # Patched archives stay local. Distribution must rebuild from the user's game.
    path = ARTIFACTS / "data/fire-ash-work/patched/Scripts.rxdata"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(output)
    json_write(ROOT / "runtime-localization-patches.json", {
        "policy": "僅修改文字顯示查詢；SygnaBuff.name、價格、等級、比較與存檔識別名稱維持原版。",
        "patches": runtime_patches, "supplemental_unique": len(runtime_targets)})
    return digest(output)


def build_font(translations, font_source="pixel"):
    from fontTools.ttLib import TTFont
    from PIL import ImageFont
    config = font_config(font_source)
    source = (ARTIFACTS / "downloads/fusion-pixel-font" / config["filename"] if font_source == "pixel" else
              ARTIFACTS / "downloads/noto-sans-cjk-tc" / config["filename"] if font_source == "noto" else
              Path(config["filename"]))
    if digest(source.read_bytes()) != config["sha256"]:
        raise ValueError("Font source hash mismatch")
    characters = set("".join(target for target, _ in translations.values()))
    with TTFont(source, fontNumber=0, recalcTimestamp=False) as font:
        expected_name = config["legacy_family"] if font_source == "noto" else config["family"]
        assert font["name"].getDebugName(1) == expected_name
        if font_source == "noto":
            assert "CFF " in font and font["OS/2"].usWeightClass == 500
        missing = sorted(c for c in characters if ord(c) >= 32 and ord(c) not in font.getBestCmap())
    if missing:
        raise ValueError("Chinese font lacks characters: " + "".join(missing))
    alpha_counts = {}
    for pixels in (12, 24):
        raster_font = ImageFont.truetype(str(source), pixels, index=0, layout_engine=ImageFont.Layout.BASIC)
        # Check unthresholded FreeType grayscale output, not a forced binary mask.
        alpha = set(bytes(raster_font.getmask("".join(sorted(characters - {'\n', '\r', '\t'})), mode="L")))
        if font_source == "pixel" and not alpha <= {0, 255}:
            raise ValueError(f"Pixel font has antialiased edges at {pixels}px: {sorted(alpha)}")
        alpha_counts[str(pixels)] = sorted(alpha)
    path = staged_font_path(font_source)
    path.parent.mkdir(parents=True, exist_ok=True)
    if font_source == "noto":
        from font_loader_audit import audit_engine
        engine_report = audit_engine(GAME / "Game.exe")
        shutil.copy2(source,path)
        assert digest(path.read_bytes()) == config["sha256"], "Noto was modified while staging"
        with TTFont(path) as installed:
            installed_missing = sorted(c for c in characters if ord(c) >= 32 and ord(c) not in installed.getBestCmap())
            assert not installed_missing and installed["OS/2"].usWeightClass == 500
        assert ImageFont.truetype(str(path),24).getname() == (config["family"],"Medium")
        license_source = source.parent / config["license_filename"]
        assert digest(license_source.read_bytes()) == config["license_sha256"]
        license_output = path.with_name("fire-ash-zhtw-OFL.txt")
        shutil.copy2(license_source,license_output)
        return {"profile": font_source,"family": config["family"],"legacy_family": config["legacy_family"],
                "style": "Medium","weight": 500,"version": config["version"],"license": "OFL-1.1",
                "asset_filename": path.name,"license_notice_file": license_output.name,
                "checked_characters": len(characters),"missing_characters": 0,"missing": installed_missing,
                "required_rare_characters": {c: ord(c) in installed.getBestCmap() for c in "戽桄"},
                "checked_actual_staged_file": True,"sha256": digest(path.read_bytes()),
                "license_sha256": digest(license_output.read_bytes()),"binary_modified": False,
                "engine_loader_audit": engine_report,"raster_sizes_px": [12,24],"api_sizes": [14,27],
                "unthresholded_freetype_alpha_values": alpha_counts,"solid_fonts_changed": False,
                "source": str(source),"publish": False,"local_trial_only": False,
                "runtime_load_tested": False}
    if font_source == "pixel":
        shutil.copy2(source, path)
    else:
        # Keep the complete Regular face, metadata and copyright; never publish it.
        with TTFont(source, fontNumber=0, recalcTimestamp=False) as font:
            font.save(path)
        with TTFont(path) as extracted, TTFont(source, fontNumber=0) as original:
            assert extracted.getBestCmap() == original.getBestCmap()
            assert extracted["name"].getDebugName(0) == original["name"].getDebugName(0)
            assert extracted["OS/2"].fsType == original["OS/2"].fsType
        notice = path.with_name(config["license_notice_file"])
        notice.write_text(
            "Microsoft JhengHei Regular — LOCAL TRIAL ONLY\n"
            "© 2022 Microsoft Corporation. All rights reserved.\n"
            "Source: this computer's C:\\Windows\\Fonts\\msjh.ttc, face 0.\n"
            "This is a complete local face extraction, not an OFL font.\n"
            "This notice grants no additional rights. Do not redistribute the font,\n"
            "any derived subset, or a package containing either. No repo or Release.\n"
            "Fusion Pixel's fire-ash-zhtw-OFL.txt does not apply and is not installed.\n",
            encoding="utf-8", newline="\n")
        return {"profile": font_source, "asset_filename": path.name, "family": config["family"], "version": config["version"],
                "license": config["license"], "license_notice_file": notice.name,
                "checked_characters": len(characters), "missing_characters": 0, "missing": [],
                "required_rare_characters": {c: ord(c) in extracted.getBestCmap() for c in "戽桄"},
                "sha256": digest(path.read_bytes()), "source_sha256": config["sha256"],
                "face_index": 0, "license_sha256": digest(notice.read_bytes()),
                "raster_sizes_px": [12, 24], "api_sizes": [14, 27], "layout_engine": "BASIC",
                "unthresholded_freetype_alpha_values": alpha_counts, "solid_fonts_changed": False,
                "source": str(source), "publish": False, "local_trial_only": True}
    license_parts = []
    for relative, expected in config["licenses"].items():
        license_path = source.parent / relative
        if digest(license_path.read_bytes()) != expected:
            raise ValueError(f"Font license hash mismatch: {relative}")
        license_parts.append(f"===== {relative} =====\n" + license_path.read_text(encoding="utf-8"))
    license_output = path.with_name("fire-ash-zhtw-OFL.txt")
    license_output.write_text("\n\n".join(license_parts), encoding="utf-8", newline="\n")
    return {"profile": font_source, "asset_filename": path.name, "family": config["family"], "version": config["version"], "license": "OFL-1.1",
            "license_notice_file": license_output.name,
            "checked_characters": len(characters), "missing_characters": 0, "missing": [],
            "sha256": digest(path.read_bytes()), "license_sha256": digest(license_output.read_bytes()),
            "native_grid_px": 12, "raster_sizes_px": [12, 24], "api_sizes": [14, 27],
            "unthresholded_freetype_alpha_values": alpha_counts, "solid_fonts_changed": False,
            "source": config["url"], "publish": False}


def audit_speakers(db, contextual_names):
    """Check both mapped names and overlooked English names against dialogue speakers."""
    names = dict(db.execute("SELECT source,target FROM catalog WHERE section=14"))
    ambiguous = {name for name, in db.execute(
        "SELECT source FROM preserved WHERE section=14 AND category='ambiguous-trainer-name'")}
    checked = skipped = 0
    problems = []
    for en, zh in db.execute("SELECT source,target FROM catalog WHERE section=0 AND target IS NOT NULL"):
        match = re.match(r"^([^:\r\n]+):", analyze_message(en)[1].strip())
        if not match or match[1] not in names:
            continue
        name = match[1]
        label = unicodedata.normalize("NFKC", re.split(r"[：:]", analyze_message(zh)[1].strip(), maxsplit=1)[0])
        checked += 1
        if names[name] is None:
            if name in ambiguous:
                skipped += 1
            elif re.search(r"[\u3400-\u9fff]", label):
                problems.append({"section": 14, "en": name, "dialogue_source": en,
                                 "dialogue_speaker": label, "issue": "English trainer name has translated speaker"})
            continue
        expected = contextual_names.get((0, en, name), unicodedata.normalize("NFKC", names[name]))
        if expected not in label:
            problems.append({"section": 0, "en": en, "zh-TW": zh, "expected_speaker": expected})
    return problems, checked, skipped


def audit_translations(db, translations):
    canonical = 0
    for line in (ROOT / "translations/reference.jsonl").read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row["section"] in (1, 5, 7, 8, 10, 12):
            assert translations[(row["section"], row["en"])][0] == row["zh-TW"], row
            canonical += 1
    prohibited = re.compile(r"精靈(?!球)|質量|信息|宝|梦|这|让|给|学|龙|鸟|电|岛|说|听|们|级|进|没|为|综|绣|内")
    problems = []
    allowed_official = 0
    for section, en, zh in db.execute("SELECT section,source,target FROM catalog WHERE target IS NOT NULL"):
        if prohibited.search(zh):
            problems.append({"section": section, "en": en, "zh-TW": zh})
        allowed_official += "精靈球" in zh
    prohibited_count = len(problems)
    species = dict(db.execute("SELECT source,target FROM catalog WHERE section=1 AND target IS NOT NULL"))
    species_pattern = re.compile(r"(?<![A-Za-z])(?:" + "|".join(
        re.escape(name) for name in sorted(species, key=len, reverse=True)) + r")(?![A-Za-z])")
    inline_checked = 0
    literal_aliases = defaultdict(set)
    contextual_names = {}
    for path in (ROOT / "translations/batches").glob("*-terms.json"):
        for term in json.loads(path.read_text(encoding="utf-8")).get("contextual_terms", []):
            contextual_names[(term["section"], term["source"], term["en"])] = unicodedata.normalize("NFKC", term["zh-TW"])
            if term["en"] == term["zh-TW"]:
                literal_aliases[(term["section"], term["source"])].add(term["en"])
    move_instructions_checked = 0
    move_names = dict(db.execute("SELECT source,target FROM catalog WHERE section=5 AND target IS NOT NULL"))
    move_patterns = (r"\bTM[0-9]+ (?:contains|is) ([^.]+)\.",
                     r"\b(?:Want|Would you like) to learn (.+?)\?",
                     r"Which Pokémon would you like me to teach (.+?)\?")
    for en, zh in db.execute("SELECT source,target FROM catalog WHERE section=0 AND target IS NOT NULL"):
        for pattern in move_patterns:
            for name in re.findall(pattern, analyze_message(en)[1]):
                if name not in move_names:
                    continue
                move_instructions_checked += 1
                if move_names[name] not in zh:
                    problems.append({"section": 0, "en": en, "zh-TW": zh, "expected_move": move_names[name]})
    speaker_problems, speakers_checked, ambiguous_speakers = audit_speakers(db, contextual_names)
    problems.extend(speaker_problems)
    alias_species_preserved = 0
    for section, en, zh in db.execute("SELECT section,source,target FROM catalog WHERE section IN (0,3,6,9,11,23,24) "
                                     "AND target IS NOT NULL AND provenance NOT LIKE 'PokeAPI/%'"):
        visible_source = analyze_message(en)[1]
        for alias in literal_aliases.get((section, en), set()):
            if alias not in zh:
                raise ValueError(f"Original creator alias changed: {alias}")
            alias_species_preserved += len(species_pattern.findall(alias))
            visible_source = visible_source.replace(alias, "")
        for name in set(species_pattern.findall(visible_source.replace(chr(0x2019), chr(39)))):
            inline_checked += 1
            if species[name] not in zh:
                problems.append({"section": section, "en": en, "zh-TW": zh, "expected_species": species[name]})
    places = defaultdict(set)
    for en, zh in db.execute("SELECT source,target FROM catalog WHERE section IN (19,20,21) AND target IS NOT NULL"):
        if len(en.split()) >= 2:
            places[en].add(unicodedata.normalize("NFKC", zh))
    place_pattern = re.compile(r"(?<![A-Za-z0-9])(?:" + "|".join(
        re.escape(name) for name in sorted(places, key=len, reverse=True)) + r")(?![A-Za-z0-9])")
    places_checked = 0
    for section, en, zh in db.execute("SELECT section,source,target FROM catalog WHERE section IN (0,23,24) AND target IS NOT NULL"):
        for name in set(place_pattern.findall(analyze_message(en)[1])):
            places_checked += 1
            contextual = contextual_names.get((section, en, name))
            expected = {contextual} if contextual else places[name]
            if not any(place in unicodedata.normalize("NFKC", zh) for place in expected):
                problems.append({"section": section, "en": en, "zh-TW": zh,
                                 "expected_place_en": name, "expected_place": sorted(expected)})
    report = {"canonical_names_checked": canonical, "prohibited_term_or_character_count": prohibited_count,
              "problem_count": len(problems),
              "official_poke_ball_exception_count": allowed_official,
              "inline_species_mentions_checked": inline_checked, "problems": problems}
    report["inline_place_mentions_checked"] = places_checked
    report["named_speakers_checked"] = speakers_checked
    report["speaker_name_conflicts"] = len(speaker_problems)
    report["ambiguous_speaker_rows_preserved"] = ambiguous_speakers
    report["move_instructions_checked"] = move_instructions_checked
    report["species_words_inside_literal_creator_aliases"] = alias_species_preserved
    json_write(ROOT / "terminology-audit.json", report)
    if problems:
        raise ValueError(f"Terminology audit failed for {len(problems)} entries; see terminology-audit.json")
    return report


def build(game, font_source="pixel"):
    manifest = json.loads((ROOT / "source-manifest.json").read_text(encoding="utf-8"))
    for name, expected in manifest["files"].items():
        if digest((game / name).read_bytes()) != expected:
            raise ValueError(f"Game changed since extraction: {name}")
    audit_full_key(game)
    db = connect()
    runtime_targets = prepare_runtime_catalog(db, game)
    missing_sources = prepare_missing_catalog(db, game)
    translations = import_translations(db, game)
    terminology_report = audit_translations(db, translations)
    preserved = [dict(zip(["section", "en", "category", "reason"], row)) for row in
                 db.execute("SELECT section,source,category,reason FROM preserved ORDER BY section,source")]
    json_write(ROOT / "translations/preserved.json", preserved)
    glossary = [{"section": section, "en": en, "zh-TW": target, "provenance": origin}
                for (section, en), (target, origin) in sorted(translations.items())
                if section in (13, 14, 18, 19, 20, 21)]
    additional_names = [{"section": section, "en": en, "zh-TW": target, "provenance": origin}
                        for (section, en), (target, origin) in sorted(translations.items())
                        if section in (4, 5, 7, 10, 100) and not origin.startswith("PokeAPI/")]
    fixed_terms = {}
    retained_terms = {}
    contextual_terms = []
    for path in sorted((ROOT / "translations/batches").glob("*-terms.json")):
        terms = json.loads(path.read_text(encoding="utf-8"))
        fixed_terms.update(terms.get("all", {}))
        retained_terms.update(terms.get("retained_terms", {}))
        contextual_terms.extend(terms.get("contextual_terms", []))
    for term in contextual_terms:
        pair = translations.get((term["section"], term["source"]))
        if pair is None or term["zh-TW"] not in pair[0]:
            raise ValueError(f"Contextual glossary does not match translation: {term}")
    teleport_terms = json.loads((ROOT / "translations/teleport-template.json").read_text(encoding="utf-8"))
    retained_terms.update({name: "原文寶可夢暱稱，保留原拼字。" for name in teleport_terms["retained_speakers"]})
    fixed_terms.update(teleport_terms["destinations"])
    retained_usage = {}
    visible_rows = [(analyze_message(target)[1], count) for target, count in db.execute(
        "SELECT COALESCE(c.target,c.source),c.occurrences FROM catalog c LEFT JOIN preserved p "
        "ON c.section=p.section AND c.source=p.source WHERE c.target IS NOT NULL OR p.source IS NOT NULL")]
    for name in retained_terms:
        pattern = re.compile(r"(?<![A-Za-z0-9])" + re.escape(name) + r"(?![A-Za-z0-9])")
        matches = [(len(pattern.findall(visible)), count) for visible, count in visible_rows]
        retained_usage[name] = {"unique_keys": sum(found > 0 for found, _ in matches),
                                "text_positions": sum(count for found, count in matches if found),
                                "mentions": sum(found * count for found, count in matches)}
    derived = [{"section": sec, "en": en, "zh-TW": zh, "source": origin}
               for (sec, en), (zh, origin) in sorted(translations.items()) if origin == "reviewed-teleport-template"]
    (ROOT / "translations/template-derived.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in derived), encoding="utf-8", newline="\n")
    json_write(ROOT / "glossary.json", {"policy": "人名、地名與劇情專有名詞以此對照為準；不改寫控制碼或代入值。",
                                       "official_exception": "精靈球為官方繁中名稱，不屬於禁止使用的舊譯精靈。",
                                       "fixed_terms": fixed_terms, "retained_terms": retained_terms,
                                       "contextual_terms": contextual_terms,
                                       "additional_name_mappings": additional_names,
                                       "additional_name_policy": "未直接取自PokeAPI的名稱對照，包含人工拼字對照、官方詞彙組合與本作自訂名稱；不宣稱全為官方命名。",
                                       "supplemental_ui_terms_file": "translations/runtime-ui.json",
                                       "retained_term_usage": retained_usage,
                                       "usage_scope": "只統計已翻譯或明確保留的文字，不把待翻英文算成刻意保留。unique_keys以區段加原文為單位。各詞可能重疊，不可直接加總作為未翻譯總數。",
                                       "terms": glossary})
    original = (game / "Data/messages.dat").read_bytes()
    data = loads(original)
    # The serializer must preserve the complete original before touching any text.
    assert writes(data) == original, "Original Marshal round-trip differs"
    changed = translate_data(data, translations)
    original_positions = [(s, m, i) for s, m, i, _ in records(data)]
    supplemental_counts = append_runtime_translations(data, translations, missing_sources)
    output = writes(data)
    assert writes(loads(output)) == output, "Translated Marshal round-trip differs"
    assert list(records(data)) == list(records(loads(output))), "Translated values changed on serialization"
    restored_records = {(s, m, i): v for s, m, i, v in records(loads(output))}
    assert all(position in restored_records for position in original_positions), "Original slot disappeared"
    original_data = loads(original)
    for section, table in enumerate(original_data):
        if table is None:
            continue
        for index, obj in enumerate(table if section == 0 else [table]):
            if isinstance(obj, UserDef):
                built = data[section][index] if section == 0 else data[section]
                old_keys = loads(obj._dump())[0]
                assert loads(built._dump())[0][:len(old_keys)] == old_keys, "Original lookup keys/order changed"
    package = ARTIFACTS / "release/fire-ash-zh-tw-preview"
    language_path = package / "Data/traditional_chinese.dat"
    language_path.parent.mkdir(parents=True, exist_ok=True)
    language_path.write_bytes(output)
    scripts_sha256 = build_scripts(game, runtime_targets, font_source)
    font_report = build_font(translations, font_source)
    rows = list(db.execute("SELECT c.section,COUNT(*),SUM(c.occurrences),"
                          "SUM(c.target IS NOT NULL),SUM(CASE WHEN c.target IS NOT NULL THEN c.occurrences ELSE 0 END),"
                          "SUM(p.source IS NOT NULL) FROM catalog c LEFT JOIN preserved p "
                          "ON c.section=p.section AND c.source=p.source GROUP BY c.section ORDER BY c.section"))
    report = {"stage": "preview", "translated_occurrences": changed,
              "total_occurrences": manifest["occurrences"], "sections": [
                  {"id": s, "category": LABELS.get(s, str(s)), "unique": n,
                   "occurrences": occurrences, "translated_unique": done,
                   "translated_occurrences": translated, "preserved_unique": kept,
                   "pending_unique": n - done - kept} for s, n, occurrences, done, translated, kept in rows],
              "checks": ["original-byte-identical-round-trip", "translated-round-trip",
                         "slot-count-and-position", "control-codes-and-placeholders"],
              "game_tested": False, "installed": False,
              "supplemental_lookup_keys": supplemental_counts,
              "total_language_slots": len(restored_records),
              "coverage_scope": "Original catalog plus native Ruby script literals, inspected dynamic trainer datasets and confirmed map gaps; not all images or game paths.",
              "preserved_categories": [dict(zip(["category", "unique_keys", "text_positions"], row)) for row in db.execute(
                  "SELECT p.category,COUNT(*),SUM(c.occurrences) FROM preserved p JOIN catalog c "
                  "ON c.section=p.section AND c.source=p.source GROUP BY p.category ORDER BY p.category")],
              "preservation_details": "translations/preserved.json",
              "supplemental_sections": {"102": {"storage": "Scripts.rxdata/FireAsh_ZHTW_Runtime",
                  "note": "工具專用分類，補充直接寫在腳本中的顯示文字。occurrences=0代表該文字不存放在原訊息檔內。"},
                  "103": {"storage": "traditional_chinese.dat/ScriptTexts", "note": "追加實際Ruby查詢鍵，保留原鍵與順序。"},
                  "104": {"storage": "traditional_chinese.dat/Map0", "note": "共用地圖缺漏文字；保留原鍵與順序。"}},
              "language_sha256": digest(output), "scripts_sha256": scripts_sha256,
              "font": font_report, "terminology": terminology_report}
    json_write(package / "coverage.json", report)
    json_write(ROOT / "coverage.json", report)
    print(json.dumps(report, ensure_ascii=False))


def self_test(font_source="pixel"):
    from PIL import ImageFont
    config = json.loads((ROOT / "font-source.json").read_text(encoding="utf-8"))
    pixel_font = ARTIFACTS / "downloads/fusion-pixel-font" / config["filename"]
    assert digest(pixel_font.read_bytes()) == config["sha256"], "Wrong pixel font source"
    for prefix in ("regular", "small"):
        pixels = config[prefix + "_raster_px"]
        assert int(config[prefix + "_font_size"] * config["engine_size_multiplier"]) == pixels
        assert pixels % config["native_grid_px"] == 0
        font = ImageFont.truetype(str(pixel_font), pixels)
        assert set(bytes(font.getmask("繁體中文，戽斗尖梭與桄榔島！", mode="L"))) <= {0, 255}
    off_grid = ImageFont.truetype(str(pixel_font), 23)
    assert set(bytes(off_grid.getmask("繁體中文", mode="L"))) - {0, 255}, "Blur regression fixture not reproduced"
    print("PASS: native pixel grids at 12/24px; mkxp 0.9 size compensation; off-grid blur reproduced")
    if font_source == "jhenghei":
        from fontTools.ttLib import TTFont
        trial = font_config(font_source)
        source = Path(trial["filename"])
        assert digest(source.read_bytes()) == trial["sha256"]
        with TTFont(source, fontNumber=0) as font:
            assert font["name"].getDebugName(1) == trial["family"]
            assert font["name"].getDebugName(2) == "Regular"
            assert all(ord(c) in font.getBestCmap() for c in "戽桄")
        for prefix in ("regular", "small"):
            pixels = trial[prefix + "_raster_px"]
            assert int(trial[prefix + "_font_size"] * 0.9) == pixels
            font = ImageFont.truetype(str(source), pixels, index=0, layout_engine=ImageFont.Layout.BASIC)
            assert set(bytes(font.getmask("繁體中文，戽桄", mode="L"))) - {0, 255}
        assert b'Microsoft JhengHei' in font_support_code(font_source)
        assert b'Fusion Pixel' in font_support_code()
        print("PASS: local JhengHei Regular face 0; 12/24px grayscale; pixel default preserved")
    elif font_source == "noto":
        from font_loader_audit import audit_engine
        from fontTools.ttLib import TTFont
        trial = font_config("noto")
        source = ARTIFACTS / "downloads/noto-sans-cjk-tc" / trial["filename"]
        assert digest(source.read_bytes()) == trial["sha256"]
        assert digest((source.parent / trial["license_filename"]).read_bytes()) == trial["license_sha256"]
        with TTFont(source) as font:
            assert "CFF " in font and font["OS/2"].usWeightClass == 500
            assert all(ord(c) in font.getBestCmap() for c in "戽桄")
        for pixels in (12,24):
            assert ImageFont.truetype(str(source),pixels).getname() == (trial["family"],"Medium")
        assert audit_engine(GAME / "Game.exe")["passed"]
        assert b'Noto font not loaded' in font_support_code("noto")
        assert b'Fusion Pixel' in font_support_code()
        print("PASS: original Noto Medium OTF; exact engine OTF scan/CFF driver; 12/24px direct load; pixel default")
    assert patch_text_layout("    if hadspace && !isspace\n" * 2).count("FireAshZHTW.cjk_boundary?") == 2
    try:
        patch_text_layout("Unexpected upstream formatter")
    except ValueError:
        pass
    else:
        raise AssertionError("Unknown upstream formatter accepted")
    validate_pair("\\bHello, \\PN! {1}\\wt[5]", "\\b你好，\\PN！{1}\\wt[5]")
    validate_pair("\\ch[75,-1,Fire,Water]", "\\ch[75,-1,火,水]")
    validate_pair("<user's cry>", "<使用者的叫聲>")
    validate_pair("\\ch[7,-1,\\PN,\\v[1]]", "\\ch[7,-1,名字\\PN,數值\\v[1]]")
    try:
        validate_pair("\\ch[7,-1,\\PN,\\v[1]]", "\\ch[7,-1,\\v[1],\\PN]")
    except ValueError:
        pass
    else:
        raise AssertionError("Menu choice variables moved between options")
    assert "Fire" in analyze_message("\\ch[75,-1,Fire,Water]")[1]
    assert analyze_message(r"Malie City\nEnjoy")[1] == "Malie City\nEnjoy"
    assert "Safari Zone Alola" not in analyze_message(r"Safari Zone\nAlola Edition")[1]
    assert "Voltorb" not in analyze_message(r"\me[Voltorb Flip win]Game clear!")[1]
    assert message_csv_fields('75,-1,"first, label","say \\"hi\\"",last') == [
        "75", "-1", "first, label", 'say "hi"', "last"]
    for bad_choice in ["\\ch[76,-1,火,水]", "\\ch[75,0,火,水]", "\\ch[75,-1,火,水,草]"]:
        try:
            validate_pair("\\ch[75,-1,Fire,Water]", bad_choice)
        except ValueError:
            pass
        else:
            raise AssertionError("Changed menu variable/cancel index/choice count accepted")
    for bad in ["你好，{1}", "\\b你好，\\PN！{2}\\wt[5]", ""]:
        try:
            validate_pair("\\bHello, \\PN! {1}\\wt[5]", bad)
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid control codes accepted")
    obj = UserDef("OrderedHash", {"@keys": [b"Hello {1}"]})
    obj._load(writes([[b"Hello {1}"], [b"Hello {1}"]]))
    data = [[obj], [None, b"Bulbasaur"]]
    translate_data(data, {(0, "Hello {1}"): ("你好，{1}", "test"),
                          (1, "Bulbasaur"): ("妙蛙種子", "test")})
    restored = loads(writes(data))
    assert loads(restored[0][0]._dump())[0] == [b"Hello {1}"]
    assert text(loads(restored[0][0]._dump())[1][0]) == "你好，{1}"
    assert text(restored[1][1]) == "妙蛙種子"
    assert restored[1][1].attributes["E"] is True
    shared = RubyString("later", {"E": True})
    linked = loads(writes([b"new bytes", shared, shared]))
    assert linked[1] is linked[2] and text(linked[2]) == "later"
    batch_source = (json.dumps({"section": 0, "en": "Hello {1}"}) + "\n").encode()
    batch = {"source_sha256": digest(batch_source), "zh-TW": ["你好，{1}"]}
    assert parse_manual_batch(batch_source, batch, {(0, "Hello {1}")})[(0, "Hello {1}")][0] == "你好，{1}"
    for invalid in [dict(batch, source_sha256="0" * 64), dict(batch, **{"zh-TW": []}),
                    dict(batch, **{"zh-TW": ["你好，{2}"]})]:
        try:
            parse_manual_batch(batch_source, invalid, {(0, "Hello {1}")})
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid translation batch accepted")
    test_db = sqlite3.connect(":memory:")
    test_db.execute("CREATE TABLE catalog(section INTEGER,source TEXT,target TEXT,provenance TEXT,occurrences INTEGER DEFAULT 1,PRIMARY KEY(section,source))")
    test_db.execute("CREATE TABLE preserved(section INTEGER,source TEXT,category TEXT,reason TEXT)")
    test_db.executemany("INSERT INTO catalog(section,source) VALUES(?,?)",
                        {(section, source) for section, _, _, source in records(source_data(GAME))})
    prepare_runtime_catalog(test_db)
    prepare_missing_catalog(test_db, ARTIFACTS / "data/fire-ash-work/original-baseline")
    translations = import_translations(test_db)
    assert test_db.execute("SELECT COUNT(*) FROM catalog WHERE section=102 AND target IS NULL").fetchone()[0] == 0
    assert translations[(5, "Psychic")][0] == "精神強念"
    assert translations[(12, "Psychic")][0] == "超能力"
    assert translations[(24, "Full")][0] == "全螢幕", "Fullscreen label regression"
    assert translations[(14, "Red")][0] == "赤紅"
    assert translations[(14, "Blue")][0] == "青綠"
    assert translations[(14, "Agatha")][0] == "菊子"
    assert translations[(14, "Lorelei")][0] == "科拿"
    assert translations[(14, "Scott")][0] == "亞希達"
    assert translations[(14, "Cheren")][0] == "黑連"
    professor_types = json.loads((ROOT / "translations/batches/130-speaker-name-terms.json").read_text(encoding="utf-8"))["professor_types"]
    for professor, trainer_type in professor_types.items():
        full_name = translations[(13, trainer_type)][0] + " " + translations[(14, professor)][0]
        assert full_name.count("博士") == 1, full_name
    speaker_db = sqlite3.connect(":memory:")
    speaker_db.execute("CREATE TABLE catalog(section INTEGER,source TEXT,target TEXT)")
    speaker_db.execute("CREATE TABLE preserved(section INTEGER,source TEXT,category TEXT)")
    speaker_db.executemany("INSERT INTO catalog VALUES(?,?,?)", [
        (14, "Agatha", None), (14, "Liza", "小南"), (14, "Drake", None),
        (0, r"\rAgatha: Hello.", r"\r菊子：你好。"),
        (0, "Liza: Hello.", "紀珂：你好。"),
        (0, r"\bDrake: Hello.", r"\b勇次：你好。")])
    speaker_db.execute("INSERT INTO preserved VALUES(14,'Drake','ambiguous-trainer-name')")
    contexts = {(0, "Liza: Hello.", "Liza"): "紀珂"}
    issues, checked, skipped = audit_speakers(speaker_db, contexts)
    assert checked == 3 and skipped == 1 and len(issues) == 1 and issues[0]["en"] == "Agatha"
    speaker_db.execute("UPDATE catalog SET target='菊子' WHERE section=14 AND source='Agatha'")
    assert audit_speakers(speaker_db, contexts)[0] == []
    assert translations[(0, r"\bWally: My Pokemon have given me courage and strength to fight. I have to win for their sake! So get ready!")][0].startswith(r"\b滿充：")
    assert translations[(0, r"\rLiza: We battle in cooperation.")][0].startswith(r"\r小南：")
    assert translations[(0, r"\rLiza: Go away. No one is allowed in this sacred land.")][0].startswith(r"\r紀珂：")
    assert translations[(0, r"\rValerie: Victory to the elegant.")][0].startswith(r"\r瑪繡：")
    assert "頭錘" in translations[(0, r"\bWant to learn Headbutt?")][0]
    assert translations[(21, "Kumquat Island")][0] == "榴柑島"
    assert translations[(21, "Trovita Gym")][0] == "柚子道館"
    assert (14, "Mark") not in translations, "UI label leaked into a trainer name"
    assert (14, "Eva") not in translations, "Stat abbreviation leaked into a trainer name"
    assert translations[(24, "forest")][0] == "forest", "Backdrop resource identifier was translated"
    assert test_db.execute("SELECT category FROM preserved WHERE section=24 AND source=?", ("forest",)).fetchone()[0] == "runtime-resource-identifier"
    assert test_db.execute("SELECT category FROM preserved WHERE section=0 AND source=?", ("Akane",)).fetchone()[0] == "trainer-name-original"
    terms = json.loads((ROOT / "translations/teleport-template.json").read_text(encoding="utf-8"))
    assert translate_teleport(r"\rMy Butterfee can Teleport you.\ch[1,-1,Fallabor,Exit]", translations, terms) == r"\r我的巴大蝶可以用瞬間移動送你前往各地。\ch[1,-1,秋葉鎮,離開]"
    assert translate_teleport(r"\bMy Eggy can Teleport you.\ch[9,0,Viridian,Cancel]", translations, terms) == r"\b我的Eggy可以用瞬間移動送你前往各地。\ch[9,0,常青市,取消]"
    assert translate_teleport(r"My Mystery can Teleport you.\ch[1,-1,Exit]", translations, terms) is None
    assert translate_teleport(r"My Alakazam can Teleport you.\ch[1,-1,Unknown,Exit]", translations, terms) is None
    print("PASS: control codes, placeholders, menu indices/counts/variables, OrderedHash keys, UTF-8, serialization, batch hashes/counts, canonical names")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["extract", "reference", "build", "self-test", "batch", "runtime-source"])
    parser.add_argument("--game", type=Path, default=GAME)
    parser.add_argument("--section", type=int, default=0)
    parser.add_argument("--limit", type=int, default=75)
    parser.add_argument("--name")
    parser.add_argument("--menu-only", action="store_true")
    parser.add_argument("--font-source", choices=("pixel", "jhenghei", "noto"), default="pixel",
                        help="Default pixel; Noto is an unmodified OTF trial; jhenghei stays local only")
    args = parser.parse_args()
    if args.action == "extract":
        extract(args.game)
    elif args.action == "reference":
        reference(args.game)
    elif args.action == "build":
        build(args.game, args.font_source)
    elif args.action == "batch":
        make_batch(args.section, args.limit, args.name, args.menu_only)
    elif args.action == "runtime-source":
        export_runtime_sources(args.game)
    else:
        self_test(args.font_source)
