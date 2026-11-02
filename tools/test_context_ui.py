"""Native Ruby context and plugin-menu regression; no game window or save writes."""
import argparse
import json
import re
import zlib
from pathlib import Path
import fire_ash as f
from ruby_vm import RubyVM
from runtime_catalog import initialize


def main(archive):
    scripts={f.text(r[1]):zlib.decompress(r[2]).decode('utf-8').replace('\r','')
             for r in f.loads(archive.read_bytes())}
    plugins={f.text(p)+'/'+f.text(n):zlib.decompress(c).decode('utf-8').replace('\r','')
             for p,m,files in f.loads((f.GAME/'Data/PluginScripts.rxdata').read_bytes()) for n,c in files}
    context=(f.ROOT/'tools/context_ui.rb').read_text(encoding='utf-8')
    assert scripts['FireAsh_ZHTW_Runtime'].endswith(context+'\n'+f.extra_text_code())
    vm=RubyVM(f.GAME)
    initialize(vm,scripts)
    vm.evaluate('''class OrderedHash < Hash
  def self._load(s)
    keys,values=Marshal.load(s); out=new
    keys.each_with_index { |k,i| out[k]=values[i] }; out
  end
end
class Messages
  def initialize(data); @messages=data; end
  def delayedLoad; end
end
module MessageTypes
  ScriptTexts=24
  def self.getFromHash(type,key); $chinese ? $messages.getFromHash(type,key) : key; end
end
module FireAshZHTW
  def self.active?; $chinese; end
end
module ClassMethodsSymbols
  def register(hash); self::DATA[hash[:id]]=new(hash); end
  def get(id); self::DATA.fetch(id); end
end
module InstanceMethods; end
class PokemonStorage; end
def pbMessage(message,commands=nil,cancel=0,skin=nil,default=0,&block)
  $seen=[message,commands,cancel,skin,default]
  $block_value=block.call if block
  result=$choice; $choice=-1; result
end
$chinese=false
'ready'
''')
    method=re.search(r'  def getFromHash\(.*?\n  end',scripts['Intl_Messages'],re.S)[0]
    vm.evaluate('class Messages\n'+method+'\nend\n"ready"')
    vm.evaluate(re.search(r'^def _INTL\(.*?^end$',scripts['Intl_Messages'],re.S|re.M)[0]+'\n"ready"')
    vm.put('$path',(f.ARTIFACTS/'release/fire-ash-zh-tw-preview/Data/traditional_chinese.dat').as_posix())
    vm.evaluate('$messages=Messages.new(Marshal.load(File.binread($path))); "ready"')
    for method in ('pbGetMonthName','pbGetAbbrevMonthName'):
        vm.evaluate(re.search(r'^def '+method+r'\(.*?^end$',scripts['Overworld_Time'],re.S|re.M)[0]+'\n"ready"')
    vm.evaluate('class PokemonStorage\n'+re.search(r'  def allWallpapers\n.*?\n  end',scripts['PokemonStorage'],re.S)[0]+'\nend\n"ready"')
    for name in ('BattleTerrain','Environment'): vm.evaluate(scripts[name]+'\n"ready"')
    english=vm.evaluate('[*(1..12).map { |m| pbGetMonthName(m) },*PokemonStorage.new.allWallpapers].join("|")')
    vm.evaluate('$chinese=true; "ready"')
    assert vm.evaluate('pbGetMonthName(5)')=='小遙'  # Reproduce the old bug before patching.
    other_months=vm.evaluate('(1..12).reject { |m| m==5 }.map { |m| pbGetMonthName(m) }.join("|")')
    vm.evaluate(context+'\n"ready"')
    assert vm.evaluate('[pbGetMonthName(5),pbGetAbbrevMonthName(5)].join("|")')=='５月|５月'
    assert vm.evaluate('[_INTL("May"),_INTL("Misty")].join("|")')=='小遙|小霞'
    assert vm.evaluate('(1..12).reject { |m| m==5 }.map { |m| pbGetMonthName(m) }.join("|")')==other_months
    assert vm.evaluate('PokemonStorage.new.allWallpapers.values_at(13,14,16).join("|")')=='機械|格紋|宇宙'
    assert vm.evaluate('[GameData::BattleTerrain.get(:Misty).name,GameData::Environment.get(:Space).name].join("|")')=='薄霧|宇宙'
    vm.evaluate('$chinese=false; "ready"')
    assert vm.evaluate('[*(1..12).map { |m| pbGetMonthName(m) },*PokemonStorage.new.allWallpapers].join("|")')==english
    assert vm.evaluate('[GameData::BattleTerrain.get(:Misty).name,GameData::Environment.get(:Space).name].join("|")')=='Misty|Space'

    # Run the plugin's actual action menu/case branch after the localization hooks load.
    lair=plugins['ZUD Plugin/[008] Dynamax Adventures/Max Lair Controls.rb']
    menu=lair[lair.index('options = ["View Map","View Party"]'):]
    menu=menu[:menu.index('          break if endgame')]
    vm.evaluate('''$Trainer=Struct.new(:party).new([])
class LairProbe
  def pbEndlessLairRecord; [2,nil,[1]]; end
  def pbLairMapScroll(*); $branch='map'; end
  def pbSummary(*); $branch='party'; end
  def pbMaxLairMenu(*); $branch='record'; end
  def pbConfirmMessage(text); $branch='leave'; true; end
  def run
    @endlessMode=true; @sprites={}; index=0; endgame=false
'''+menu+'''
    $original_options=options
    endgame
  end
end
'ready'
''')
    for chinese in (False,True):
        for choice,branch in [(0,'map'),(1,'party'),(2,'record'),(3,'leave'),(-1,'none')]:
            vm.evaluate(f'$chinese={str(chinese).lower()}; $choice={choice}; $branch="none"; LairProbe.new.run; "ready"')
            assert vm.evaluate('$branch')==branch
            assert vm.evaluate('$original_options.join("|")')=='View Map|View Party|View Record|Leave Lair'
            expected='查看地圖|查看隊伍|查看紀錄|離開巢穴' if chinese else 'View Map|View Party|View Record|Leave Lair'
            assert vm.evaluate('$seen[1].join("|")')==expected
            assert vm.evaluate('$seen[2].to_s')=='-1'
    vm.evaluate('$chinese=true; $choice=2; pbMessage("No save file was found.",nil,7,"skin",3) { 123 }; "ready"')
    assert vm.evaluate('$seen.join("|")')=='找不到存檔。||7|skin|3'
    assert vm.evaluate('$block_value.to_s')=='123'
    assert vm.evaluate('pbMessage("Unrelated text"); $seen[0]')=='Unrelated text'
    assert vm.evaluate('FireAshZHTW::DIRECT_PLUGIN_MESSAGES.all? { |text| pbMessage(text); $seen[0]==_INTL(text) && $seen[0]!=text }.to_s')=='true'
    rows=[json.loads(line) for line in (f.ROOT/'translation-source/batches/147-runtime-missing.jsonl').read_text(encoding='utf-8').splitlines()]
    targets=json.loads((f.ROOT/'translations/batches/147-runtime-missing.json').read_text(encoding='utf-8'))['zh-TW']
    for row,target in zip(rows,targets):
        vm.put('$key',row['en'])
        assert vm.evaluate('_INTL($key,"PIKA")')==target.replace('{1}','PIKA')
    report={'passed':True,'plugin_menu_branches_checked':10,'new_plugin_keys_checked':len(rows),'direct_plugin_messages_checked':4,
            'months_and_names_checked':True,'wallpaper_and_terrain_context_checked':True,
            'english_behavior_unchanged':True,'control_codes_and_parameters_preserved':True,
            'scripts_sha256':f.digest(archive.read_bytes()),'game_started':False}
    f.json_write(f.ROOT/'context-ui-validation.json',report)
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scripts',type=Path,default=f.ARTIFACTS/'data/fire-ash-work/patched/Scripts.rxdata')
    main(parser.parse_args().scripts)
