"""Run actual core/ZUD/RTT trainer factories with native Ruby, without launching the game."""
import argparse
import json
import re
import zlib
from pathlib import Path

import fire_ash as f
from ruby_vm import RubyVM


def main(archive):
    spec = json.loads((f.ROOT / 'translations/npc-nicknames.json').read_text(encoding='utf-8'))
    source = f.GAME / 'Data/trainers.dat'
    assert f.digest(source.read_bytes()) == spec['source_sha256']
    translations, preserved = spec['translations'], spec['preserved']
    assert not (translations.keys() & preserved.keys())
    for en, zh in translations.items():
        f.validate_pair(en, zh)
        assert re.search('[\u3400-\u9fff]', zh), (en, zh)
    scripts = [(f.text(r[1]), zlib.decompress(r[2]).decode('utf-8').replace('\r', ''))
               for r in f.loads(archive.read_bytes())]
    runtime = dict(scripts)['FireAsh_ZHTW_Runtime']
    hook = (f.ROOT / 'tools/npc_nicknames.rb').read_text(encoding='utf-8')
    assert hook in runtime, 'Packaged nickname hook is stale or absent'
    table = re.search(r'module FireAshZHTW\n  NPC_NICKNAMES = .*?\nend\n', runtime, re.S)[0]
    core = next(code for name, code in scripts if name == 'Trainer' and 'def to_trainer' in code)
    plugins = []
    plugin_blob = (f.GAME / 'Data/PluginScripts.rxdata').read_bytes()
    assert f.digest(plugin_blob) == '1b955ab8f42392f5b5b3a9a199285e208907a2faedd460dfd2519e5e8523eb6c'
    for plugin, metadata, files in f.loads(plugin_blob):
        for name, packed in files:
            code = zlib.decompress(packed).decode('utf-8').replace('\r', '')
            if 'def to_trainer' in code:
                plugins.append((f.text(plugin), code))
    assert [name for name, _ in plugins] == ['ZUD Plugin', 'Randomized Trainer Teams']
    vm = RubyVM(f.GAME)
    vm.evaluate('''
module FireAshZHTW
  def self.active?; $chinese; end
end
module Settings; RIVAL_NAMES=[]; end
module MultipleForms
  def self.hasFunction?(*); false; end
end
module GameData
  class Trainer
    def name; @real_name; end
    def lose_text; @real_lose_text; end
  end
  class Species
    def self.get(id); Struct.new(:species,:id_number).new(id,1); end
  end
  class TrainerType
    def self.get(id); Struct.new(:id_number).new(1); end
  end
  class Nature; DATA=(0...50).to_a; end
  class Stat
    def self.each_main
      [:HP,:ATTACK,:DEFENSE,:SPECIAL_ATTACK,:SPECIAL_DEFENSE,:SPEED].each { |id| yield Struct.new(:id).new(id) }
    end
  end
end
class NPCTrainer
  attr_accessor :id,:items,:lose_text,:party,:trainer_type
  def initialize(name,type); @name=name; @trainer_type=type; @party=[]; end
  def male?; true; end
end
class Pokemon
  IV_STAT_LIMIT=31; EV_LIMIT=510
  attr_accessor :forced_form,:form_simple,:item,:ability_index,:ability,:passive,:gender,
    :shiny,:square_shiny,:nature,:iv,:ev,:happiness,:dynamax_lvl,:gmaxfactor,:acepkmn,:poke_ball
  def initialize(species,level,trainer,flag)
    @species=species; @level=level; @iv={}; @ev={}; @moves=[]
  end
  def species_data; GameData::Species.get(@species); end
  def speciesName; @species.to_s; end
  def learn_move(move); @moves << move; end
  def reset_moves; @moves=[:DEFAULT]; end
  def makeShadow; @shadow=true; end
  def update_shadow_moves(*); @shadow_moves=true; end
  def calc_stats; @stats_calculated=true; end
end
def pbBallTypeToItem(id); Struct.new(:id).new(id); end
NoSoftReset=false; FirstGuaranteed=false
$Trainer=Object.new
def $Trainer.make_foreign_ID; 12345; end
$game_variables=[]
'ready'
''')
    pokemon = dict(scripts)['Pokemon']
    for name in ('name', 'name=', 'nicknamed?'):
        method = re.search(r'  def ' + re.escape(name) + r'(?:\n|\().*?\n  end', pokemon, re.S)[0]
        vm.evaluate('class Pokemon\n' + method + '\nend\n"ready"')
    vm.put('$path', source.as_posix())
    vm.evaluate('$data=Marshal.load(File.binread($path)); $records=$data.values.uniq; "ready"')
    names = vm.evaluate('$records.flat_map { |t| t.instance_variable_get(:@pokemon).filter_map { |p| p[:name] } }.uniq.join("\\n")').splitlines()
    assert set(names) == translations.keys() | preserved.keys()
    vm.put('$porygon', 'Porygon Zero')
    vm.evaluate('$case=$records.find { |t| t.instance_variable_get(:@pokemon).any? { |p| p[:name]==$porygon } }; "ready"')

    def load_factory(code):
        method = re.search(r'    def to_trainer\b.*?(?=\n  end\nend)', code, re.S)[0]
        vm.evaluate('class GameData::Trainer\n' + method + '\nend\n"ready"')

    load_factory(core)
    assert vm.evaluate('$chinese=true; $case.to_trainer.party.map(&:name).join("|")').find('Porygon Zero') >= 0
    vm.evaluate(table + hook + '\n"ready"')
    assert vm.evaluate('$case.to_trainer.party.map(&:name).join("|")').find('多邊獸零號') >= 0
    counts = []
    for label, code in [('core', core)] + plugins:
        load_factory(code)  # Later plugin def must not bypass our prepend.
        counts.append(vm.evaluate('''
checked=0
$records.each do |record|
  # Clone because RTT itself temporarily edits its source array for random teams.
  before=Marshal.dump(record)
  srand(1234); $chinese=false; english=Marshal.load(before).to_trainer
  srand(1234); $chinese=true; chinese=Marshal.load(before).to_trainer
  raise 'party size' unless english.party.length==chinese.party.length
  english.party.zip(chinese.party).each do |old,new|
    raw=old.instance_variable_get(:@name)
    expected=FireAshZHTW::NPC_NICKNAMES.fetch(raw,raw)
    raise "nickname #{raw}" unless new.instance_variable_get(:@name)==expected
    checked+=1 if raw && !raw.empty?
    new.instance_variable_set(:@name,raw) if old.instance_variable_defined?(:@name)
    raise 'non-name Pokemon properties changed' unless Marshal.dump(old)==Marshal.dump(new)
  end
  raise 'trainer fields changed' unless Marshal.dump(english)==Marshal.dump(chinese)
  raise 'shared data mutated' unless Marshal.dump(record)==before
end
checked.to_s
'''))
        print('PASS:', label, counts[-1], 'named team members; other properties identical')
    # User-chosen names never use the NPC factory, even if they match a translated nickname.
    assert vm.evaluate('$chinese=true; p=Pokemon.new(:PORYGON,34,nil,false); p.name="Porygon Zero"; p.name') == 'Porygon Zero'
    # An unknown custom NPC nickname must remain unchanged.
    assert vm.evaluate('r=Marshal.load(Marshal.dump($case)); r.instance_variable_get(:@pokemon)[0][:name]="My Custom Name"; r.to_trainer.party[0].name') == 'My Custom Name'
    font_path = f.ARTIFACTS / 'data/fire-ash-work/fonts/fire-ash-zhtw.otf'
    from fontTools.ttLib import TTFont
    font = TTFont(font_path)
    missing = {c for zh in translations.values() for c in zh if ord(c) not in font.getBestCmap()}
    assert not missing, missing
    report = {'passed': True, 'unique_nicknames': len(names), 'translated': len(translations),
              'preserved': preserved, 'factory_named_members': dict(zip(['core']+[p[0] for p in plugins],map(int,counts))),
              'trainer_records': int(vm.evaluate('$records.length.to_s')),
              'plugin_order_verified': True, 'player_nickname_unchanged': True,
              'english_unchanged': True, 'non_name_properties_unchanged': True,
              'font_missing_characters': [], 'scripts_sha256': f.digest(archive.read_bytes()),
              'source_sha256': spec['source_sha256'], 'game_started': False}
    f.json_write(f.ROOT / 'npc-nickname-validation.json', report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scripts', type=Path, default=f.ARTIFACTS / 'data/fire-ash-work/patched/Scripts.rxdata')
    main(parser.parse_args().scripts)
