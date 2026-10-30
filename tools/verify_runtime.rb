# encoding: UTF-8
# No window, save data, filesystem writes, or actual game variables are used.
module MessageTypes
  ScriptTexts = 24
  def self.getFromHash(_type, key)
    return key unless FireAshZHTW.active?
    value = $fire_ash_data[24][key]
    value ? value.dup.force_encoding('UTF-8') : key
  end
end
eval($fire_ash_intl_method, TOPLEVEL_BINDING)
eval($fire_ash_runtime, TOPLEVEL_BINDING)
eval($fire_ash_sygna_class, TOPLEVEL_BINDING)
eval($fire_ash_sygna_methods, TOPLEVEL_BINDING)

module GameData
  class Stat
    def self.get(id); Struct.new(:name).new(id.to_s); end
  end
end
def pbGet(id); $runtime_test_variables[id]; end
def pbSet(id, value); $runtime_test_variables[id] = value; end
def pbMessage(text); $runtime_test_messages << text; 0; end

$runtime_test_variables = {}
$runtime_test_messages = []
$PokemonSystem.language = 0
setUpBuffShop
before = pbGet(62).map { |buff| [buff.name,buff.buff_type,buff.level,buff.cost,buff.stat] }
showShopBuffs
english_menu = $runtime_test_messages.last
raise 'English display changed' unless english_menu.include?("Warrior's Blessing Lv. 1 - 7 GC Credits")
raise 'English description changed' unless pbGet(62)[6].display_description == "Your Pokémon can't be poisoned."

$PokemonSystem.language = 1
showShopBuffs
chinese_menu = $runtime_test_messages.last
raise 'Dynamic menu was not translated' unless chinese_menu.include?('戰士祝福 等級１ - 7 點數') && !chinese_menu.include?('WHICH BUFF')
raise 'Internal buff identifiers changed' unless before == pbGet(62).map { |buff| [buff.name,buff.buff_type,buff.level,buff.cost,buff.stat] }
payload = chinese_menu[/\\ch\[([^\]]*)\]/,1]
raise 'Choice control missing' unless payload
fields = []
fields << pbCsvField!(payload) until payload.empty?
raise 'Choice variable/index changed' unless fields[0,2] == ['75','-1']
raise 'Choice count/order changed' unless fields[2..].length == before.length && fields[2].start_with?('戰士祝福')
raise 'Description not translated' unless pbGet(62)[6].display_description == '你的寶可夢不會中毒。'
legacy = SygnaBuff.new('Antitoxin'.b,"Your Pokémon can't be poisoned.".b,10)
raise 'Legacy byte-string description not translated' unless legacy.display_description == '你的寶可夢不會中毒。'
raise 'Stored encoding was mutated' unless legacy.description.encoding.name == 'ASCII-8BIT'

pbSet(80,100)
pbSet(75,0)
buyBuff
raise 'Price changed' unless pbGet(80) == 93
raise 'Stored identifier changed' unless pbGet(58)[0].name == "Warrior's Blessing Lv. 1"
raise 'Level upgrade identifier changed' unless pbGet(62)[0].name == "Warrior's Blessing Lv. 2"
raise 'Level upgrade rules changed' unless pbGet(62)[0].level == 2 && pbGet(62)[0].cost == 35
raise 'Purchase message not translated' unless $runtime_test_messages.last.include?('已購買戰士祝福 等級１')
equipBuff
raise 'Equip energy changed' unless pbGet(57)[0] == 6 && hasActiveBuff("Warrior's Blessing Lv. 1")
unequipBuff
raise 'Unequip state changed' unless pbGet(57)[0] == 7 && !hasActiveBuff("Warrior's Blessing Lv. 1")
pbGet(57)[0] = 0
equipBuff
raise 'Low-energy dynamic message not translated' unless $runtime_test_messages.last.include?('還需要1點能量')
raise 'Failed equip changed state' unless pbGet(57)[0] == 0 && !hasActiveBuff("Warrior's Blessing Lv. 1")

bag_key = 'Choose new quantity of {1} (max. #{Settings::BAG_MAX_PER_SLOT}).'
bag = FireAshZHTW.intl(bag_key, {'#{Settings::BAG_MAX_PER_SLOT}'=>999}, '傷藥')
raise 'Positional/interpolated values lost' unless bag.include?('傷藥') && bag.include?('999') && !bag.include?('#{') && !bag.include?('Choose')
legacy_bag = FireAshZHTW.intl(bag_key.b, {'#{Settings::BAG_MAX_PER_SLOT}'=>999}, '傷藥'.b)
raise 'Legacy interpolation encoding failed' unless legacy_bag == bag
box_key = 'Box #{match[0]+1}#{spacer}[#{match[1]}]'
box = FireAshZHTW.intl(box_key, {'#{match[0]+1}'=>3,'#{spacer}'=>' ','#{match[1]}'=>'1/30'})
raise 'Multiple interpolations failed' unless box == '盒子3 [1/30]'
energy_key = 'NEED #{diff} MORE ENERGY TO EQUIP THIS BUFF.'
raise 'Energy count not translated' unless FireAshZHTW.intl(energy_key, {'#{diff}'=>2}).include?('還需要2點能量')
region = FireAshZHTW.text('Hoenn ')
raise 'Region padding/translation failed' unless region == '豐緣 '
title = _INTL('{1}Club Completion No.{2}{3}',region,7,'A')
raise 'Region header not translated' unless title.include?('豐緣 俱樂部通關第7號A')
$PokemonSystem.language = 0
raise 'English interpolation behavior changed' unless FireAshZHTW.intl(bag_key, {'#{Settings::BAG_MAX_PER_SLOT}'=>999}, 'Potion') == 'Choose new quantity of Potion (max. 999).'
raise 'English region changed' unless FireAshZHTW.text('Hoenn ') == 'Hoenn '
'PASS: dynamic UI lookups, translated shop choices/descriptions, unchanged internal names/prices/levels/energy, English fallback'
