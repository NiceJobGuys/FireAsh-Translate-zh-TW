# encoding: UTF-8
# Runs the game's actual formatter with FreeType glyph advances, without Game.exe.
Color = Struct.new(:red, :green, :blue, :alpha) do
  def initialize(red,green,blue,alpha=255); super(red,green,blue,alpha); end
end
Rect = Struct.new(:x, :y, :width, :height)
class Font
  attr_writer :bold, :italic, :color
  def bold; @bold || false; end
  def italic; @italic || false; end
  def color; @color ||= Color.new(255,255,255,255); end
  def self.exist?(_name); true; end
  def self.default_color; Color.new(255,255,255,255); end
end
class Bitmap
  attr_writer :font
  def disposed?; false; end
  def fire_ash_zhtw_text_size(text)
    small = font.size == 14
    widths = small ? $fire_ash_small_widths : $fire_ash_glyph_widths
    height = small ? $fire_ash_small_height : $fire_ash_font_height
    Rect.new(0,0,text.each_char.sum { |char| widths.fetch(char) },height)
  end
end

eval($fire_ash_original_draw, TOPLEVEL_BINDING)
original_fast = method(:getFormattedTextFast)
original_formatted = method(:getFormattedText)
$PokemonSystem.language = 1
bitmap = Bitmap.new
sample = '這是一段沒有空白的繁體中文對話，應該完整顯示並且正常換行。'
baseline = original_fast.call(bitmap,13,7,110,-1,sample,32)
raise 'Original overflow was not reproduced' unless baseline.any? { |c| c[0] != "\n" && c[1]+c[3]-2 > 123 }
Object.send(:remove_const, :FORMATREGEXP)
eval($fire_ash_patched_draw, TOPLEVEL_BINDING)

fixtures = [sample, '「中文標點」不可出現在錯誤的行首，或讓（括號）留在行尾。',
            '小智與Pikachu一起旅行，HP已回復。', "明確換行\n下一段沒有空白的中文對話。",
            "這裡有停頓\001以及繼續顯示的中文對話。",
            '這是卡璞・鳴鳴和卡璞・哞哞的戰鬥。']
$fire_ash_layout_cases_checked = fixtures.length * 2
fixtures.each do |text|
  [false,true].each do |formatted|
    input = formatted ? '<b>'+text+'</b>' : text
    rows = getFormattedText(bitmap,13,7,110,-1,input,32)
    glyphs = rows.reject { |c| c[0] == "\n" }
    raise 'Text lost while wrapping' unless glyphs.map { |c| c[0] }.join == text.delete("\n")
    raise 'CJK text still overflows' unless glyphs.all? { |c| c[1] >= 13 && c[1]+c[3]-2 <= 123 }
    raise 'CJK text did not wrap' unless glyphs.map { |c| c[2] }.uniq.length > 1
    glyphs.group_by { |c| c[2] }.each_value do |line|
      raise 'Closing punctuation at line start' if FireAshZHTW::NO_LINE_START.include?(line.first[0])
      raise 'Opening punctuation at line end' if FireAshZHTW::NO_LINE_END.include?(line.last[0])
    end
  end
end
plain = getFormattedTextFast(bitmap,0,0,110,-1,sample,32,true,true)
raise 'Explicit-only wrapping changed' unless plain.map { |c| c[2] }.uniq.length == 1
['English words wrap exactly as before.', 'A short line.'].each do |text|
  raise 'English fast layout changed' unless original_fast.call(bitmap,13,7,110,-1,text,32) == getFormattedTextFast(bitmap,13,7,110,-1,text,32)
  tagged = '<b>'+text+'</b>'
  raise 'English formatted layout changed' unless original_formatted.call(bitmap,13,7,110,-1,tagged,32) == getFormattedText(bitmap,13,7,110,-1,tagged,32)
end
'PASS: original CJK overflow reproduced; native plain/formatted wrapping, punctuation, mixed text, explicit breaks, wait codes, English layout'
