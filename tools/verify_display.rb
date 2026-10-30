# encoding: UTF-8
# Execute original/patched game painters, including their actual shadow passes.
class Bitmap
  attr_reader :display_calls
  def clear_display_calls; @display_calls = []; end
  def fire_ash_zhtw_draw_text(x,y,w,h,text,align=0)
    @display_calls ||= []
    @display_calls << ['text',x,y,w,h,text,align,font.name,font.size,*font.color.to_a]
  end
  def fill_rect(x,y,w,h,color)
    @display_calls ||= []
    @display_calls << ['rect',x,y,w,h,'',0,'',0,*color.to_a]
  end
end

Object.send(:remove_const, :FORMATREGEXP)
eval($fire_ash_original_draw, TOPLEVEL_BINDING)
original = {}
[:pbDrawShadowText, :renderLineBrokenChunksWithShadow, :drawSingleFormattedChar,
 :pbDrawOutlineText].each { |name| original[name] = method(name) }
Object.send(:remove_const, :FORMATREGEXP)
eval($fire_ash_patched_draw, TOPLEVEL_BINDING)
patched = original.keys.to_h { |name| [name, method(name)] }
base = Color.new(80,80,88,255)
shadow = Color.new(160,160,168,255)
$fire_ash_display_cases = 0
[0,1].each do |language|
  $PokemonSystem.language = language
  bitmap = Bitmap.new
  character = getFormattedText(bitmap,32,72,448,-1,'字',32).first
  character[8], character[9] = base, shadow
  fixtures = {
    :pbDrawShadowText => [bitmap,32,72,200,32,'設定',base,shadow],
    :renderLineBrokenChunksWithShadow => [bitmap,32,72,[['設定',0,0,48,32]],0,base,shadow],
    :drawSingleFormattedChar => [bitmap,character]
  }
  fixtures.each do |name,args|
    bitmap.clear_display_calls
    original[name].call(*args)
    before = bitmap.display_calls.dup
    raise 'Original three-pass shadow not reproduced' unless before.length == 4
    bitmap.clear_display_calls
    patched[name].call(*args)
    expected = language == 1 ? [before.last] : before
    raise "Base glyph changed or shadow retained: #{name}" unless bitmap.display_calls == expected
    $fire_ash_display_cases += 1
  end
  [1,2].each do |flag|
    character[16] = flag
    bitmap.clear_display_calls
    original[:drawSingleFormattedChar].call(bitmap,character)
    before = bitmap.display_calls.dup
    bitmap.clear_display_calls
    patched[:drawSingleFormattedChar].call(bitmap,character)
    raise 'Formatted outline changed' unless bitmap.display_calls == before && before.length == 9
    $fire_ash_display_cases += 1
  end
  bitmap.clear_display_calls
  original[:pbDrawOutlineText].call(bitmap,32,72,200,32,'設定',base,shadow)
  before = bitmap.display_calls.dup
  bitmap.clear_display_calls
  patched[:pbDrawOutlineText].call(bitmap,32,72,200,32,'設定',base,shadow)
  raise 'Menu outline changed' unless bitmap.display_calls == before && before.length == 9
  $fire_ash_display_cases += 1
end

class Window_DrawableCommand
  attr_reader :contents
  def initialize(*_args); @contents = Bitmap.new; end
  def drawCursor(_index,rect); rect; end
  def baseColor; Color.new(80,80,88,255); end
  def shadowColor; Color.new(160,160,168,255); end
end
eval($fire_ash_options_code, TOPLEVEL_BINDING)
module Graphics
  class << self
    attr_accessor :fullscreen, :scale, :screen, :centered
    def resize_screen(w,h); self.screen = [w,h]; end
    def center; self.centered = true; end
  end
end
Settings.const_set(:SCREEN_WIDTH, 512)
Settings.const_set(:SCREEN_HEIGHT, 384)
class << $PokemonSystem
  attr_accessor :screensize
end
eval($fire_ash_resize_code, TOPLEVEL_BINDING)
def _INTL(text, *args)
  (FireAshZHTW.active? && $fire_ash_preview_ui[text]) || text
end
$PokemonSystem.language = 0
scale_option = eval($fire_ash_scale_option_code, TOPLEVEL_BINDING)
raise 'Old scale indices changed' unless scale_option.values == ['S','M','L','XL','Full','3x']
6.times do |value|
  $PokemonSystem.screensize = -1
  scale_option.set(value)
  raise 'Scale setting lost' unless scale_option.get == value
  if value == 4
    raise 'Fullscreen index changed' unless Graphics.fullscreen
  else
    raise 'Scale changed' unless Graphics.scale == (value+1)*0.5 && !Graphics.fullscreen
  end
end
raise 'Invalid legacy scale changed' unless FireAshZHTW.screen_factor(99) == 4
$ResizeInitialized = false
$PokemonSystem.screensize = 5
Graphics.fullscreen = true
eval($fire_ash_startup_resize_code, TOPLEVEL_BINDING)
raise '3x did not survive startup' unless Graphics.scale == 3.0 && !Graphics.fullscreen
raise 'Internal resolution changed' unless Graphics.screen == [512,384]

$PokemonSystem.language = 1
raise 'Fullscreen label uses capacity translation' unless eval($fire_ash_scale_option_code).values[4] == '全螢幕'
ui = $fire_ash_preview_ui
options = [
  SliderOption.new(ui['Music Volume'],0,100,5,nil,nil),
  SliderOption.new(ui['SE Volume'],0,100,5,nil,nil),
  EnumOption.new(ui['Text Speed'],['Slow','Normal','Fast'].map { |s| ui[s] },nil,nil),
  EnumOption.new(ui['Battle Effects'],['On','Off'].map { |s| ui[s] },nil,nil),
  EnumOption.new(ui['Battle Style'],['Switch','Set'].map { |s| ui[s] },nil,nil),
  EnumOption.new(ui['Default Movement'],['Walking','Running'].map { |s| ui[s] },nil,nil),
  eval($fire_ash_scale_option_code),
  EnumOption.new(ui['Text Entry'],['Cursor','Keyboard'].map { |s| ui[s] },nil,nil)
]
$fire_ash_preview_calls = {}
[:before,:after].each do |mode|
  painter = mode == :before ? original : patched
  Object.send(:define_method, :pbDrawShadowText, painter[:pbDrawShadowText])
  window = Window_PokemonOption.new(options,0,64,512,304)
  [100,80,1,0,0,0,5,1].each_with_index { |value,i| window.setValueNoRefresh(i,value) }
  bitmap = window.contents
  bitmap.clear_display_calls
  pbDrawShadowText(bitmap,32,16,448,32,ui['Options'],base,shadow)
  8.times { |i| window.drawItem(i,8,Rect.new(32,64+i*36,448,32)) }
  $fire_ash_preview_calls["settings-#{mode}"] = bitmap.display_calls.dup
  bitmap.clear_display_calls
  characters = getFormattedText(bitmap,32,268,448,-1,$fire_ash_preview_dialogue,32)
  characters.each do |ch|
    ch[8], ch[9] = base, shadow
    painter[:drawSingleFormattedChar].call(bitmap,ch)
  end
  $fire_ash_preview_calls["dialogue-#{mode}"] = bitmap.display_calls.dup
end
Object.send(:define_method, :pbDrawShadowText, patched[:pbDrawShadowText])
'PASS: 12 native painter cases; Chinese shadows removed, English/explicit outlines preserved; six scale choices, 3x startup at 512x384'
