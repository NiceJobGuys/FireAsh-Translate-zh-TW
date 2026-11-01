"""Native regression of lookup strings and actual patched display callers."""
import json
import re
import sys
import zlib
from datetime import datetime, timezone

import fire_ash as f
from ruby_vm import RubyVM
from runtime_catalog import entries, initialize

sys.stdout.reconfigure(encoding='utf-8')
baseline = f.ARTIFACTS / 'data/fire-ash-work/original-baseline'
archive = f.ARTIFACTS / 'data/fire-ash-work/patched/Scripts.rxdata'
language = f.ARTIFACTS / 'release/fire-ash-zh-tw-preview/Data/traditional_chinese.dat'
report_path = f.ROOT / 'runtime-coverage-validation.json'


def main():
    scripts = {f.text(r[1]): zlib.decompress(r[2]).decode('utf-8').replace('\r','')
               for r in f.loads(archive.read_bytes())}
    originals = {f.text(r[1]): zlib.decompress(r[2]).decode('utf-8').replace('\r','')
                 for r in f.loads((baseline/'Data/Scripts.rxdata').read_bytes())}
    vm = RubyVM(f.GAME)
    initialize(vm, scripts)
    vm.evaluate('''class OrderedHash < Hash
  def self._load(s)
    keys, values = Marshal.load(s)
    out = new
    keys.each_with_index { |key,i| out[key] = values[i] }
    out
  end
end
class Messages
  def initialize(data); @messages=data; end
  def delayedLoad; end
end
module FireAshZHTW
  def self.active?; $audit_chinese; end
end
module MessageTypes
  ScriptTexts=24
  def self.getFromHash(type,key); ($audit_chinese ? $new_messages : $old_messages).getFromHash(type,key); end
  def self.getFromMapHash(type,key); ($audit_chinese ? $new_messages : $old_messages).getFromMapHash(type,key); end
end
'ready'
''')
    intl=scripts['Intl_Messages']
    for name in ('getFromHash','getFromMapHash'):
        method=re.search(r'  def '+name+r'\(.*?\n  end',intl,re.S)[0]
        vm.evaluate('class Messages\n'+method+'\nend\n"ready"')
    for name in ('_INTL','_MAPINTL'):
        method=re.search(r'^def '+name+r'\(.*?^end$',intl,re.S|re.M)[0]
        vm.evaluate(method+'\n"ready"')
    vm.evaluate('$new_data=Marshal.load(File.binread('+f.ruby_string(language.as_posix())+')); '+
                '$old_data=Marshal.load(File.binread('+f.ruby_string((baseline/'Data/messages.dat').as_posix())+')); '+
                '$new_messages=Messages.new($new_data); $old_messages=Messages.new($old_data); $audit_chinese=true; "ready"')
    assert vm.evaluate('_INTL("Entry")') == '報名參賽'
    assert vm.evaluate('_INTL("No Entry")') == '取消報名'
    missing=[]
    checked=0
    lookup_sources = list(scripts.items())
    for plugin, metadata, files in f.loads((f.GAME/'Data/PluginScripts.rxdata').read_bytes()):
        lookup_sources.extend((f.text(plugin)+'/'+f.text(name),zlib.decompress(code).decode('utf-8')) for name,code in files)
    for name,code in lookup_sources:
        for line,kind,key in entries(vm,code):
            if kind not in ('_INTL','_ISPRINTF') or not re.search('[A-Za-z]',key):
                continue
            vm.put('$key',key)
            if vm.evaluate('$new_data[24].key?($key).to_s')!='true':
                missing.append([name,line,key])
            checked+=1
    assert not missing, missing
    print('PASS: native static lookups:',checked,'missing: 0')
    supplemental=[]
    glossary=json.loads((f.ROOT/'glossary.json').read_text(encoding='utf-8'))
    names={r['en']:r['zh-TW'] for r in glossary['terms'] if r['section']==14}
    names.update(glossary['fixed_terms'])
    names.update(json.loads((f.ROOT/'runtime-translation-notes.json').read_text(encoding='utf-8'))['speaker_overrides'])
    speakers_checked=0
    for path in sorted((f.ROOT/'translations/batches').glob('*-runtime-missing.json')):
        raw=(f.ROOT/'translation-source/batches'/path.with_suffix('.jsonl').name).read_bytes()
        rows=[json.loads(l) for l in raw.decode().splitlines()]
        translations=json.loads(path.read_text(encoding='utf-8'))
        f.parse_manual_batch(raw,translations,{(r['section'],r['en']) for r in rows})
        for row,zh in zip(rows,translations['zh-TW']):
            for speaker in re.findall(r'\\[br]([^:]+): ',row['en']):
                target=names[speaker]
                if speaker=='Drake' and row['script']=='PWC Battle' and row['line']>500:
                    target='勇次'
                assert target+'：' in zh,(row,zh,target)
                speakers_checked+=1
            vm.put('$key',row['en']);vm.put('$target',zh)
            lookup='$new_data[24][$key]' if row['section']==103 else '$new_data[0][0][$key]'
            assert vm.evaluate(f'({lookup} == $target).to_s')=='true',row
            supplemental.append(row)
    print('PASS: all',len(supplemental),'supplemental targets match native table')

    # Exercise the actual pickup/receipt methods with a no-filesystem bag and message sink.
    vm.evaluate('''class String
  def starts_with_vowel?; self =~ /^[aeiou]/i; end
end
class PokemonBag
  def self.pocketNames; [nil,nil,nil,nil,nil,'樹果']; end
  def pbStoreItem(item,quantity); $bag_requests << [item,quantity]; true; end
end
module GameData
  class Item
    def self.get(id); new; end
    def name; '莓莓果'; end
    def name_plural; name; end
    def pocket; 5; end
    def move; nil; end
    def is_key_item?; false; end
    def is_machine?; false; end
  end
end
def pbMessage(text); $audit_output << text; end
$PokemonBag=PokemonBag.new
$bag_requests=[]; $audit_output=[]
'ready'
''')
    for method in ('pbItemBall','pbReceiveItem'):
        code=re.search(r'^def '+method+r'\(.*?^end$',scripts['Overworld'],re.S|re.M)[0]
        vm.evaluate(code+'\n"ready"')
        old=vm.evaluate(f'$audit_chinese=false; {method}(:PECHABERRY); $audit_output.last')
        new=vm.evaluate(f'$audit_chinese=true; {method}(:PECHABERRY); $audit_output.last')
        assert old.startswith('You put the 莓莓果')
        assert new==r'你將莓莓果收進\n<icon=bagPocket5>\c[1]樹果口袋\c[0]。',repr(new)
    assert vm.evaluate('$bag_requests.length.to_s')=='4'
    print('PASS: actual pbItemBall/pbReceiveItem, control codes, item quantity, English fallback')

    command=re.search(r'  def command_102\n.*?\n  end',scripts['Interpreter_Commands'],re.S)[0]
    vm.evaluate('''module Input
  def self.update; end
end
class MissingChoiceTest
  attr_reader :branch
  def run(choices,cancel)
    @index=0; @branch={}; @list=[Struct.new(:indent,:parameters).new(2,[choices,cancel])]
    command_102
    @branch[2]
  end
  def pbShowCommands(window, choices, cancel)
    $choice_output=choices; $choice_cancel=cancel
    1
  end
'''+command+'\nend\n$choice_test=MissingChoiceTest.new\n"ready"')
    choices=json.loads((f.ROOT/'translation-source/standalone-choices.json').read_text(encoding='utf-8'))
    preserved={r['en'] for r in json.loads((f.ROOT/'translations/preserved.json').read_text(encoding='utf-8')) if r['section']==0}
    for row in choices:
        vm.evaluate('$game_map=Struct.new(:map_id).new('+str(row['map'])+'); '+
                    '$choice_input=['+','.join(f.ruby_string(x) for x in row['choices'])+']; "ready"')
        english=vm.evaluate('$audit_chinese=false; $choice_test.run($choice_input,4); $choice_output.join("|")')
        chinese=vm.evaluate('$audit_chinese=true; $choice_test.run($choice_input,4); $choice_output.join("|")')
        assert english=='|'.join(row['choices'])
        assert chinese!=english and all(not re.search('[A-Za-z]',label) or label in preserved
                                       for label in chinese.split('|')),(row,chinese)
        assert vm.evaluate('($choice_input.join("|") == '+f.ruby_string(english)+').to_s')=='true'
        assert vm.evaluate('[$choice_cancel,$choice_test.branch[2],$choice_output.length].join(",")')==f'4,1,{len(row["choices"])}'
    print('PASS: all',len(choices),'independent menus, English/order/cancel/index/nonmutation')

    # The actual localized option name must still select the correct description branch.
    method=re.search(r'  def showBuffDescription\(buffName\).*?\n  end',scripts['UI_EnemyBuffs'],re.S)[0]
    vm.evaluate('class BuffDescriptionTest\n def initialize; @sprites={"textbox"=>Struct.new(:text).new}; end\n'+
                'def text; @sprites["textbox"].text; end\n'+method+'\nend\n$buff_test=BuffDescriptionTest.new\n"ready"')
    for label,expected in [('Attack Buff','攻擊'),('Defense Buff','防禦'),('Sp. Attack Buff','特攻'),
                           ('Sp. Defense Buff','特防'),('Speed Buff','速度'),('Accuracy Buff','命中率'),
                           ('Evasion Buff','閃避率'),('Status Immunity','異常狀態'),('Interference Immunity','畏縮'),('Vigilance','要害')]:
        vm.put('$buff_label',label)
        english=vm.evaluate('$audit_chinese=false; $buff_test.showBuffDescription(_INTL($buff_label)); $buff_test.text')
        chinese=vm.evaluate('$audit_chinese=true; $buff_test.showBuffDescription(_INTL($buff_label)); $buff_test.text')
        assert english.startswith('Enemy Pokémon'),english
        assert expected in chinese and 'Enemy' not in chinese,chinese
    print('PASS: 10 localized enemy-buff branches and English behavior')
    header_line=next(line.strip() for line in scripts['UI_ShowChallengeTeam'].splitlines() if 'textPositions.push([_INTL(header)' in line)
    vm.evaluate('module Graphics; def self.width; 512; end; end; BASECOLOR=nil; SHADOWCOLOR=nil; "ready"')
    for row in (r for r in supplemental if r.get('script')=='UI_ShowChallengeTeam'):
        vm.put('$header',row['en'])
        for chinese_mode in (False,True):
            packed=vm.evaluate('$audit_chinese='+str(chinese_mode).lower()+'; header=$header; textPositions=[]; '+header_line+'; textPositions[0][0..3].join("|")')
            label,x,y,align=packed.split('|')
            assert int(x)==(256 if chinese_mode else 256-5*len(row['en'])) and int(align)==(2 if chinese_mode else 0)
            assert (not re.search('[A-Za-z]',label)) if chinese_mode else label==row['en']
    map_key=next(r['en'] for r in supplemental if r['section']==104)
    vm.put('$key',map_key)
    for mid in (141,151,214):
        assert '這是你的隊伍' in vm.evaluate(f'$audit_chinese=true; _MAPINTL({mid},$key)')
    # Changes stay in the approved script blocks; all other scripts remain byte-identical.
    allowed={'Settings','DrawText','Interpreter_Commands','Minigame_VoltorbFlip','EditorScreens',
             'EditorScreens_SpritePositioning','Debug_MenuSpriteRenamer','UI_EnemyBuffs','UI_ShowChallengeTeam'}
    patches=json.loads((f.ROOT/'runtime-localization-patches.json').read_text(encoding='utf-8'))['patches']
    allowed.update(p['script'] for p in patches)
    assert all(code==scripts[name] for name,code in originals.items() if name not in allowed)
    return {'passed':True,'static_calls_checked':checked,'missing_static_calls':missing,
            'supplemental_keys_checked':len(supplemental),'standalone_menus_checked':len(choices),
            'speaker_mentions_checked':speakers_checked,
            'enemy_buff_branches_checked':10,'pickup_receipt_methods_checked':2,'map_fallbacks_checked':3,
            'english_behavior_unchanged':True,'game_started':False,'installed':False,
            'language_sha256':f.digest(language.read_bytes()),'scripts_sha256':f.digest(archive.read_bytes()),
            'validated_at_utc':datetime.now(timezone.utc).isoformat(),
            'scope':'Native static calls and inspected dynamic datasets; not exhaustive gameplay/image coverage.'}


if __name__=='__main__':
    try:
        report=main()
    except Exception as error:
        f.json_write(report_path,{'passed':False,'error':str(error)})
        raise
    f.json_write(report_path,report)
    print('PASS: runtime coverage regression')
