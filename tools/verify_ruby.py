"""Use the bundled Ruby DLL for data/syntax validation without starting the game."""
import argparse
import ctypes
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT.parents[1]
GAME = Path(r"D:\Games\Pokemon Fire Ash\Pokemon Fire Ash 3.7")
sys.path.insert(0, str(ARTIFACTS / "downloads/fire-ash-python"))
from rubymarshal.reader import loads
import zlib
import fire_ash


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game", type=Path, default=GAME, help="Hash-checked original build baseline")
    args = parser.parse_args()
    source_game = args.game.resolve()
    baseline = json.loads((ROOT / "source-manifest.json").read_text(encoding="utf-8"))
    for relative, expected in baseline["files"].items():
        assert fire_ash.digest((source_game / relative).read_bytes()) == expected, f"Original baseline changed: {relative}"
    dll_directory = os.add_dll_directory(str(GAME))
    ruby = ctypes.CDLL(str(GAME / "x64-msvcrt-ruby300.dll"))
    stack = ctypes.c_void_p()
    ruby.ruby_init_stack.argtypes = [ctypes.c_void_p]
    ruby.ruby_init_stack(ctypes.byref(stack))
    ruby.ruby_setup.restype = ctypes.c_int
    if ruby.ruby_setup() != 0:
        raise RuntimeError("Ruby initialization failed")
    # ruby_options finishes the builtin prelude (including Object#clone).
    # Ruby 3.0.2 embedding API: ruby/ruby doc/extension.rdoc, tag v3_0_2.
    os.environ.pop("RUBYOPT", None)
    ruby.ruby_options.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_char_p)]
    ruby.ruby_options.restype = ctypes.c_void_p
    bootstrap_args = (ctypes.c_char_p * 5)(b"ruby", b"--disable-gems", b"-e", b"", None)
    ruby.ruby_options(4, bootstrap_args)
    ruby.rb_eval_string_protect.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_int)]
    ruby.rb_eval_string_protect.restype = ctypes.c_size_t
    ruby.rb_string_value_cstr.argtypes = [ctypes.POINTER(ctypes.c_size_t)]
    ruby.rb_string_value_cstr.restype = ctypes.c_char_p
    ruby.rb_errinfo.restype = ctypes.c_size_t
    ruby.rb_obj_as_string.argtypes = [ctypes.c_size_t]
    ruby.rb_obj_as_string.restype = ctypes.c_size_t
    ruby.rb_utf8_str_new.argtypes = [ctypes.c_char_p, ctypes.c_longlong]
    ruby.rb_utf8_str_new.restype = ctypes.c_size_t
    ruby.rb_gv_set.argtypes = [ctypes.c_char_p, ctypes.c_size_t]

    def evaluate(code):
        state = ctypes.c_int()
        source = ("# encoding: UTF-8\n" + code).encode("utf-8")
        value = ctypes.c_size_t(ruby.rb_eval_string_protect(source, ctypes.byref(state)))
        if state.value:
            error = ctypes.c_size_t(ruby.rb_obj_as_string(ruby.rb_errinfo()))
            raise RuntimeError(ruby.rb_string_value_cstr(ctypes.byref(error)).decode("utf-8", errors="replace")[:1800])
        return ruby.rb_string_value_cstr(ctypes.byref(value)).decode("utf-8")

    ruby_version = evaluate("RUBY_VERSION")
    print("Ruby:", ruby_version)
    literal_probe = '#{1+1} #$fire_ash_literal_canary #@fire_ash_literal_canary 中文'
    evaluate("$fire_ash_literal_canary=123; @fire_ash_literal_canary=456; 'probe ready'")
    assert evaluate(fire_ash.ruby_string(literal_probe)) == literal_probe, "Ruby dictionary quoting interpolated data"
    stub = """class OrderedHash < Hash
  def self._load(s)
    keys, values = Marshal.load(s)
    out = new
    keys.each_with_index { |key, i| out[key] = values[i] }
    out
  end
end
'ready'
"""
    evaluate(stub)
    package = ARTIFACTS / "release/fire-ash-zh-tw-preview"
    path = (package / "Data/traditional_chinese.dat").as_posix()
    check = f"""
a = Marshal.load(File.binread({json.dumps(path)}))
$fire_ash_data = a
raise 'Wrong section count' unless a.length == 102
raise 'Wrong translation encoding' unless a[1][1].encoding.name == 'UTF-8'
raise 'Wrong species name' unless a[1][1] == '妙蛙種子'
raise 'Wrong move name' unless a[5][1].force_encoding('UTF-8') == '超級角擊'
raise 'Wrong UI translation' unless a[24]['Bag'].force_encoding('UTF-8') == '背包'
raise 'Wrong intro translation' unless a[0][1]['\\\\bWelcome to the world of Pokémon.'].force_encoding('UTF-8') == '\\\\b歡迎來到寶可夢的世界。'
'PASS: Ruby Marshal.load, OrderedHash lookup, species, move, UI, intro'
"""
    print(evaluate(check))
    native_records = evaluate("""
parts = []
$fire_ash_data.each_with_index do |table, section|
  next if table.nil?
  tables = section == 0 ? table.each_with_index.to_a : [[table, nil]]
  tables.each do |obj, map_id|
    next if obj.nil?
    values = obj.is_a?(Hash) ? obj.values : obj
    values.each_with_index do |value, index|
      next if value.nil? || value.empty?
      value = value.dup.force_encoding('UTF-8')
      parts << [section, map_id || -1, index, value.bytesize].join(':') + ':' + value + "\\n"
    end
  end
end
parts.join
""")
    data = loads((package / "Data/traditional_chinese.dat").read_bytes())
    expected = "".join(f"{s}:{-1 if m is None else m}:{i}:{len(value.encode('utf-8'))}:{value}\n"
                       for s, m, i, value in fire_ash.records(data))
    assert native_records == expected, "Native Ruby data differs from the Python build"
    print("PASS: all", sum(1 for _ in fire_ash.records(data)), "text slots match native Ruby")
    scripts_path = ARTIFACTS / "data/fire-ash-work/patched/Scripts.rxdata"
    if scripts_path.exists():
        scripts = loads(scripts_path.read_bytes())
        for _, name, compressed in scripts:
            script = zlib.decompress(compressed)
            value = ruby.rb_utf8_str_new(script, len(script))
            ruby.rb_gv_set(b"$fire_ash_script", value)
            try:
                evaluate("RubyVM::InstructionSequence.compile($fire_ash_script); 'ok'")
            except RuntimeError as error:
                raise RuntimeError(f"{name!r}: {error}") from error
        print("PASS: Ruby syntax for", len(scripts), "script blocks")
    font_scripts = [zlib.decompress(row[2]) for row in scripts
                    if fire_ash.text(row[1]) == "FireAsh_ZHTW_Font"]
    assert len(font_scripts) == 1, "Missing or duplicate Chinese font support script"
    assert font_scripts[0] == (ROOT / "tools/font_support.rb").read_bytes(), "Build is stale; rebuild font support first"
    font_code = font_scripts[0].decode("utf-8")
    message_code = next(zlib.decompress(row[2]).decode("utf-8").replace("\r", "")
                        for row in scripts if fire_ash.text(row[1]) == "Messages")
    csv_method = re.search(r"^def pbCsvField!\(str\).*?(?=^def pbCsvPosInt!)", message_code, re.S | re.M)
    assert csv_method, "Cannot locate the original game CSV reader"
    evaluate(csv_method[0] + "\n'CSV reader ready'")
    csv_fixtures = ["75,-1,Normal, Fire, Water", '75,-1,"first, label","say \\"hi\\"",last',
                    "77,Default Beats,Spring Violin,Summer Flute", "1,-1,\\PN,\\v[1]",
                    "1,-1, ", '1,-1,"中文, 選項",下一個']
    for payload in csv_fixtures:
        encoded = payload.encode("utf-8")
        ruby.rb_gv_set(b"$fire_ash_csv", ruby.rb_utf8_str_new(encoded, len(encoded)))
        native = evaluate("s=$fire_ash_csv.dup; fields=[]; fields << pbCsvField!(s) until s.empty?; fields.join(30.chr)")
        assert native.split("\x1e") == fire_ash.message_csv_fields(payload), payload
    print("PASS: message CSV parsing matches the game for", len(csv_fixtures), "quoted/escaped/Unicode fixtures")
    font_stub = """
class Font
  attr_accessor :name, :size, :bold, :italic
  def initialize(name='Power Green', size=29)
    @name, @size = name, size
  end
end
class Bitmap
  attr_reader :font, :drawn_font, :drawn_style
  attr_accessor :fail_draw
  def initialize
    @font = Font.new
  end
  def draw_text(*args)
    @drawn_font = [font.name, font.size]
    @drawn_style = [font.bold, font.italic]
    raise 'simulated draw failure' if @fail_draw
    :drawn
  end
  def text_size(*args)
    [font.name, font.size]
  end
end
module Settings
  LANGUAGES = [['English', 'english.dat'], ['繁體中文', 'traditional_chinese.dat']]
end
"""
    evaluate(font_stub + "\n'font stub ready'")
    evaluate(font_code + "\n'font hook ready'")
    print(evaluate("""
$PokemonSystem = Struct.new(:language).new(0)
raise 'English font changed' unless Font.new.name == 'Power Green' && Font.new.size == 29
$PokemonSystem.language = 1
f = Font.new
raise 'Chinese font missing' unless f.name == FireAshZHTW::FONT && f.size == 27
f.name = 'Power Green Narrow'
f.size = 25
raise 'Chinese setter failed' unless f.name == FireAshZHTW::FONT && f.size == 27
FireAshZHTW::PIXEL_SIZES.each_with_index do |api_size, i|
  raise 'Non-native raster grid' unless (api_size * 0.9).to_i == 12 * (i+1)
  raise 'Size changes when applied twice' unless FireAshZHTW.size(api_size) == api_size
end
$PokemonSystem.language = 0
f.name = 'Power Green'
f.size = 29
raise 'English setters changed' unless f.name == 'Power Green' && f.size == 29
b = Bitmap.new
raise 'English draw failed' unless b.draw_text(0,0,100,30,'English') == :drawn
raise 'English text changed' unless b.drawn_font == ['Power Green',29]
raise 'Chinese menu metrics failed' unless b.text_size('繁體中文') == [FireAshZHTW::FONT,27]
raise 'Font not restored after metrics' unless [b.font.name,b.font.size] == ['Power Green',29]
b.draw_text(0,0,100,30,'繁體中文'.dup.force_encoding('ASCII-8BIT'))
raise 'Chinese menu label failed' unless b.drawn_font == [FireAshZHTW::FONT,27]
raise 'Font not restored after drawing' unless [b.font.name,b.font.size] == ['Power Green',29]
b.font.bold = true
b.font.italic = true
b.draw_text(0,0,100,30,'粗體斜體測試')
raise 'Synthetic style damaged pixel grid' unless b.drawn_style == [false,false]
raise 'Font styles not restored' unless b.font.bold && b.font.italic
b.draw_text(0,0,100,30,'English')
raise 'English styles changed' unless b.drawn_style == [true,true]
b.fail_draw = true
begin
  b.draw_text(0,0,100,30,'繁體中文')
rescue RuntimeError
end
raise 'Font not restored after failure' unless [b.font.name,b.font.size] == ['Power Green',29]
raise 'Styles not restored after failure' unless b.font.bold && b.font.italic
b.fail_draw = false
$PokemonSystem.language = 1
b.draw_text(0,0,100,30,'切換後的既有文字')
raise 'Existing bitmap font not updated after language change' unless b.drawn_font == [FireAshZHTW::FONT,27]
'PASS: language-specific fonts; Chinese menu label, metrics, UTF-8/legacy text, restoration after draw failure'
"""))
    original_scripts = loads((source_game / "Data/Scripts.rxdata").read_bytes())
    original_draw = next(zlib.decompress(row[2]).decode("utf-8") for row in original_scripts
                         if fire_ash.text(row[1]) == "DrawText")
    patched_draw = next(zlib.decompress(row[2]).decode("utf-8") for row in scripts
                        if fire_ash.text(row[1]) == "DrawText")
    assert patched_draw == fire_ash.patch_text_layout(original_draw), "Text layout build is stale"
    for name, code in [(b"$fire_ash_original_draw", original_draw), (b"$fire_ash_patched_draw", patched_draw)]:
        encoded = ("# encoding: UTF-8\n" + code).encode("utf-8")
        ruby.rb_gv_set(name, ruby.rb_utf8_str_new(encoded, len(encoded)))
    from PIL import ImageFont
    font_path = ARTIFACTS / "data/fire-ash-work/fonts/fire-ash-zhtw.ttf"
    font_sha256 = fire_ash.digest(font_path.read_bytes())
    assert font_sha256 == json.loads((ROOT / "coverage.json").read_text(encoding="utf-8"))["font"]["sha256"], "Stale font build"
    raster_font = ImageFont.truetype(str(font_path), 24)
    visible_characters = set("".join(value for _, _, _, value in fire_ash.records(data)))
    visible_characters.update((ROOT / "tools/verify_layout.rb").read_text(encoding="utf-8"))
    metrics = {c: raster_font.getlength(c) for c in visible_characters}
    assert all(width == int(width) for width in metrics.values()), "Fractional glyph advances"
    evaluate("$fire_ash_glyph_widths = {" + ",".join(
        fire_ash.ruby_string(c) + "=>" + str(int(width)) for c, width in metrics.items()) + "}; 'metrics ready'")
    print(evaluate((ROOT / "tools/verify_layout.rb").read_text(encoding="utf-8")))
    layout_cases_checked = int(evaluate("$fire_ash_layout_cases_checked.to_s"))
    preview_text = "這是桄榔島的戽斗尖梭。小智與皮卡丘一起旅行，歡迎來到寶可夢的世界！"
    preview_rows = evaluate("getFormattedText(Bitmap.new,32,272,448,-1," + fire_ash.ruby_string(preview_text) +
                            ",32).reject { |c| c[0] == 10.chr }.map { |c| [c[0].ord,c[1],c[2],c[3],c[4]].join(',') }.join(10.chr)")
    native_layout = [[int(field) for field in line.split(",")] for line in preview_rows.splitlines()]
    assert "".join(chr(row[0]) for row in native_layout) == preview_text
    assert all(x >= 32 and x + width - 2 <= 480 and y + height <= 368
               for _, x, y, width, height in native_layout), "Preview dialogue overflow"
    fire_ash.json_write(ARTIFACTS / "data/fire-ash-work/font-preview-layout.json", {
        "text": preview_text, "rows": native_layout, "font_sha256": fire_ash.digest(font_path.read_bytes()),
        "source": "Original game getFormattedText + CJK wrap patch + actual FreeType advances at 24px"})
    runtime_scripts = [zlib.decompress(row[2]) for row in scripts
                       if fire_ash.text(row[1]) == "FireAsh_ZHTW_Runtime"]
    runtime_targets = json.loads((ROOT / "translations/runtime-ui.json").read_text(encoding="utf-8"))["102"]
    assert len(runtime_scripts) == 1 and runtime_scripts[0] == fire_ash.runtime_support_code(runtime_targets), "Runtime UI build is stale"
    intl_code = next(zlib.decompress(row[2]).decode("utf-8").replace("\r", "") for row in scripts
                     if fire_ash.text(row[1]) == "Intl_Messages")
    intl_method = re.search(r"^def _INTL\(\*arg\).*?^end$", intl_code, re.S | re.M)
    sygna_code = next(zlib.decompress(row[2]).decode("utf-8").replace("\r", "") for row in scripts
                      if fire_ash.text(row[1]) == "Sygna Buffs")
    sygna_class = re.search(r"^class SygnaBuff\b.*?^end$", sygna_code, re.S | re.M)
    assert intl_method and sygna_class, "Cannot locate original localization/buff definitions"
    methods = []
    for name in ["setUpBuffShop", "showShopBuffs", "buyBuff", "viewOwnedBuffs", "equipBuff", "unequipBuff",
                 "buffInArray", "ownedBuff", "hasActiveBuff", "buffInShop", "shouldAddToBuffShop?", "shopUpdate?"]:
        method = re.search(r"^def " + re.escape(name) + r"(?=[(\s]).*?^end$", sygna_code, re.S | re.M)
        assert method, f"Missing buff method: {name}"
        methods.append(method[0])
    for name, code in [(b"$fire_ash_runtime", runtime_scripts[0].decode("utf-8")),
                       (b"$fire_ash_intl_method", intl_method[0]),
                       (b"$fire_ash_sygna_class", sygna_class[0]),
                       (b"$fire_ash_sygna_methods", "\n".join(methods))]:
        encoded = ("# encoding: UTF-8\n" + code).encode("utf-8")
        ruby.rb_gv_set(name, ruby.rb_utf8_str_new(encoded, len(encoded)))
    print(evaluate((ROOT / "tools/verify_runtime.rb").read_text(encoding="utf-8")))
    native_runtime = evaluate("FireAshZHTW::RUNTIME_TEXT.sort.map { |en,zh| en.bytesize.to_s+':'+en+zh.bytesize.to_s+':'+zh+10.chr }.join")
    expected_runtime = "".join(f"{len(en.encode('utf-8'))}:{en}{len(zh.encode('utf-8'))}:{zh}\n"
                               for en, zh in sorted(runtime_targets.items()))
    assert native_runtime == expected_runtime, "Native Ruby supplemental dictionary differs from JSON"
    print("PASS: all", len(runtime_targets), "supplemental UI entries match native Ruby")
    report = {"ruby_version": ruby_version, "native_slots_checked": sum(1 for _ in fire_ash.records(data)),
              "scripts_syntax_checked": len(scripts), "font_hook_behavior": "pass",
              "native_message_csv_cases_checked": len(csv_fixtures),
              "native_cjk_layout_cases_checked": layout_cases_checked, "english_layout_unchanged_cases_checked": 4,
              "original_cjk_overflow_reproduced": True, "layout_metrics": "FreeType-Fusion-Pixel-12px-zh-TW-at-24px",
              "layout_test_sha256": fire_ash.digest((ROOT / "tools/verify_layout.rb").read_bytes()),
              "runtime_ui_unique_checked": len(runtime_targets), "runtime_display_behavior": "pass",
              "runtime_support_sha256": fire_ash.digest(runtime_scripts[0]),
              "runtime_test_sha256": fire_ash.digest((ROOT / "tools/verify_runtime.rb").read_bytes()),
              "game_started": False, "installed": False,
              "validated_at_utc": datetime.now(timezone.utc).isoformat(),
              "language_sha256": fire_ash.digest((package / "Data/traditional_chinese.dat").read_bytes()),
              "scripts_sha256": fire_ash.digest(scripts_path.read_bytes()),
              "font_support_sha256": fire_ash.digest(font_scripts[0]),
              "verifier_sha256": fire_ash.digest(Path(__file__).read_bytes()),
              "font_source_sha256": fire_ash.digest((ROOT / "font-source.json").read_bytes()),
              "font_sha256": font_sha256,
              "original_baseline": str(source_game)}
    fire_ash.json_write(ROOT / "validation.json", report)
    # Keep the DLL search handle alive until all calls have completed.
    dll_directory.close()


if __name__ == "__main__":
    main()
