"""Native regression for translations/extra-text.json and tools/extra_text.rb."""
import json
import re
import sys
import zlib

import fire_ash as f
from ruby_vm import RubyVM

STUBS = r'''
module FireAshZHTW
  class << self; attr_accessor :on; end
  def self.active?; @on; end
  def self.display_string(v); v; end
end
TABLE = { "Summary" => "查看能力", "{1} Performance" => "{1}的表現", "[{1}]" => "[{1}]",
          "{1} boosted its {2}{3} using its Z-Power!" => "{1}使用Ｚ力量，提高了{2}{3}！",
          "{1}Club Completion No.{2}{3}" => "{1}俱樂部完成第{2}號{3}" }
def _INTL(*arg)
  s = (FireAshZHTW.active? && TABLE[arg[0]] || arg[0]).dup
  (1...arg.length).each { |i| s.gsub!("{#{i}}", arg[i].to_s) }
  s
end
MAP_TABLES = { 208 => { "You managed to survive the crash." => "你成功在墜落中倖存。" },
               209 => { "Hello." => "你好。" } }
module MessageTypes
  def self.getFromMapHash(mapid, key); (MAP_TABLES[mapid] || {}).fetch(key, key); end
end
def _MAPINTL(mapid, *arg)
  return _INTL(*arg) unless MAP_TABLES.key?(mapid)
  s = MessageTypes.getFromMapHash(mapid, arg[0]).dup
  (1...arg.length).each { |i| s.gsub!("{#{i}}", arg[i].to_s) }
  s
end
class Interpreter
  attr_accessor :map_id, :seen
  def execute_command; @seen = _MAPINTL($current_map, @text); end
  def show(text); @text = text; execute_command; @seen; end
end
def pbDrawTextPositions(bitmap, textpos); $drawn = textpos.map { |t| t[0] }; end
def pbDrawShadowText(bitmap, x, y, w, h, string, *rest); $shadow = string; end
def drawTextEx(bitmap, x, y, w, n, text, *rest); $ex = text; end
class Window_CommandPokemon
  attr_reader :commands
  def initialize(commands, width = nil); @commands = commands; end
  def commands=(v); @commands = v; end
end
class Window_PhoneList < Window_CommandPokemon; end
class Window_UnformattedTextPokemon
  attr_reader :text
  def initialize(text = ""); @text = text; end
  def text=(v); @text = v; end
end
class Window_AdvancedTextPokemon
  attr_reader :text
  def setText(v); @text = v; end
  def text=(v); setText(v); end
end
'ready'
'''

CHECKS = r'''
def eq(a, b, what); raise "#{what}: #{a.inspect} != #{b.inspect}" unless a == b; end
Z = FireAshZHTW
Z.on = false
eq _INTL("Any"), "Any", "English mode _INTL"
eq Window_CommandPokemon.new(["Catch", "Don't Catch"]).commands, ["Catch", "Don't Catch"], "English commands"
Z.on = true
# Literal UI and missing keys
eq _INTL("{1} happily carried you across the water.", "噴火龍"), "噴火龍開心地載著你渡過了水面。", "missing _INTL key"
eq _MAPINTL(47, "Feel my power!"), "感受我的力量吧！", "_MAPINTL"
eq _INTL("Summary"), "查看能力", "table still wins"
# English _INTL arguments
eq _INTL("{1} Performance", "Psychic"), "超能力的表現", "Meloetta splash"
eq _INTL("[{1}]", "Any"), "[不限]", "raid filter"
eq _INTL("{1}", "Raid: Lv. 3"), "團體戰：等級3", "raid level pattern"
eq _INTL("{1} boosted its {2}{3} using its Z-Power!", "噴火龍", "攻擊", " sharply"), "噴火龍使用Ｚ力量，大幅提高了攻擊！", "Z-Power override"
eq _INTL("{1} boosted its {2}{3} using its Z-Power!", "噴火龍", "能力", ""), "噴火龍使用Ｚ力量，提高了能力！", "Z-Power no boost"
eq _INTL("{1}Club Completion No.{2}{3}", "關都 ", 2, " - Veteran"), "關都 俱樂部完成第2號－資深", "record difficulty"
eq _INTL("{1}", 5), "5", "non-string args"
# Windows
list = ["Select", "Summary", "Back"]
w = Window_CommandPokemon.new(list)
eq w.commands, ["選擇", "查看能力", "返回"], "command window"
eq list, ["Select", "Summary", "Back"], "caller array untouched"
same = ["寶可夢", "背包"]
raise "unchanged list must keep identity" unless Window_CommandPokemon.new(same).commands.equal?(same)
w.commands = ["Train", "Details", "Don't Train", "Back"]
eq w.commands, ["訓練", "詳細資料", "不訓練", "返回"], "commands="
eq Window_PhoneList.new(["Professor Oak"]).commands, ["大木博士"], "subclass"
eq Window_UnformattedTextPokemon.new("Can't place that there.").text, "無法放在那裡。", "unformatted init"
u = Window_UnformattedTextPokemon.new; u.text = "All boxes are full."
eq u.text, "所有盒子都已滿。", "unformatted text="
a = Window_AdvancedTextPokemon.new; a.text = "The heavy rain has lifted!"
eq a.text, "大雨停了！", "advanced text"
a.text = "要套用篩選條件，還是開始搜尋？ [Level_Filter_Applied] [Shiny_Filter_Applied]"
eq a.text, "要套用篩選條件，還是開始搜尋？ [等級篩選] [異色篩選]", "fragments"
a.text = "Unknown English stays"
eq a.text, "Unknown English stays", "passthrough"
# Draw helpers (ability splash, Max Lair, Voltorb Flip)
pos = [["噴火龍的", 0, 0], ["Sandy Brawn Gain", 0, 32], [nil, 0, 0]]
pbDrawTextPositions(nil, pos)
eq $drawn, ["噴火龍的", "沙塵體魄強化", nil], "ability splash"
pbDrawShadowText(nil, 0, 0, 1, 1, "Level 4")
eq $shadow, "等級4", "Voltorb Flip level"
drawTextEx(nil, 0, 0, 1, 1, "Balanced Training", 0, 0)
eq $ex, "均衡訓練", "drawTextEx"
# Event on map 208 transfers the player to 209, then shows text that lives in 208's table.
ev = Interpreter.new; ev.map_id = 208; $current_map = 209
eq ev.show("You managed to survive the crash."), "你成功在墜落中倖存。", "text after transfer"
eq ev.show("Hello."), "你好。", "destination table still wins when it has the key"
eq ev.show("Unknown line."), "Unknown line.", "miss in both stays English"
eq Z.event_map, nil, "event map restored after the command"
$current_map = 208
eq ev.show("You managed to survive the crash."), "你成功在墜落中倖存。", "no transfer"
Z.on = false
$current_map = 209
eq ev.show("You managed to survive the crash."), "You managed to survive the crash.", "English mode keeps the game's lookup"
Z.on = true
"PASS: extra text (missing keys, map keys, _INTL arguments, override, patterns, fragments, windows, draws, text after an event transfer); English mode untouched"
'''

HOOKED = ["_INTL", "_MAPINTL", "pbDrawTextPositions", "pbDrawShadowText", "drawTextEx"]
PREPENDED = {"Interpreter": ["execute_command"],
             "Window_CommandPokemon": ["initialize", "commands="], "Window_UnformattedTextPokemon": ["initialize", "text="],
             "Window_AdvancedTextPokemon": ["setText"]}


def later_sources(scripts_path):
    rows = f.loads(scripts_path.read_bytes())
    names = [f.text(r[1]) for r in rows]
    later = [(names[i], zlib.decompress(r[2]).decode("utf-8", "replace"))
             for i, r in enumerate(rows) if i > names.index("FireAsh_ZHTW_Runtime")]
    later += [(f.text(p[0]) + "/" + f.text(s[0]), zlib.decompress(s[1]).decode("utf-8", "replace"))
              for p in f.loads((f.GAME / "Data/PluginScripts.rxdata").read_bytes()) for s in p[2]]
    return later


def check_later_definitions(scripts_path):
    # A later top-level bare def would drop the alias chain; a later alias of a prepended
    # method would recurse. Either silently breaks the translation, so refuse.
    for name, code in later_sources(scripts_path):
        for meth in HOOKED:
            assert not re.search(r"^def\s+%s\b" % re.escape(meth), code, re.M), f"{name} redefines {meth}"
        cls = None
        for line in code.splitlines():
            m = re.match(r"\s*class\s+(\w+)", line)
            cls = m.group(1) if m else cls
            for meth in PREPENDED.get(cls, []):
                assert not re.search(r"\balias(_method)?\b.*\b%s(?!\w)" % re.escape(meth.rstrip("=")), line), \
                    f"{name} aliases prepended {cls}#{meth}"


def check_table_consistency(language):
    extra = json.loads((f.ROOT / "translations/extra-text.json").read_text(encoding="utf-8"))
    table = {}
    for section, data in enumerate(f.loads(language.read_bytes())):
        for obj in (data if section == 0 and data else [data]) or []:
            if isinstance(obj, f.UserDef):
                keys, values = f.loads(obj._dump())
                table.update((f.text(k), f.text(v)) for k, v in zip(keys, values))
    clashes = {en: (zh, table[en]) for en, zh in extra["text"].items() if en in table and table[en] != zh}
    assert not clashes, f"text keys must match the language table or move to override: {clashes}"
    assert all(en in table for en in extra["override"]), "override keys must exist in the language table"
    return len(extra["text"]), len(extra["override"])


def main():
    scripts_path = f.ARTIFACTS / "data/fire-ash-work/patched/Scripts.rxdata"
    if "--scripts" in sys.argv:
        scripts_path = f.Path(sys.argv[sys.argv.index("--scripts") + 1])
    vm = RubyVM(f.GAME)
    vm.evaluate(STUBS)
    vm.put("$src", f.extra_text_code())
    vm.evaluate("eval($src); 'ready'")
    print(vm.evaluate(CHECKS))
    runtime = next(zlib.decompress(r[2]).decode("utf-8") for r in f.loads(scripts_path.read_bytes())
                   if f.text(r[1]) == "FireAsh_ZHTW_Runtime")
    assert f.extra_text_code() in runtime, "built runtime block lacks the current extra text"
    check_later_definitions(scripts_path)
    print("PASS: no later script or plugin redefines the aliased helpers or aliases the prepended window methods")
    n, o = check_table_consistency(f.GAME / "Data/traditional_chinese.dat")
    print(f"PASS: {n} text entries agree with the language table where keys overlap; {o} reviewed override(s)")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
