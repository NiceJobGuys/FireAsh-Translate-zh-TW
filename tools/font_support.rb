# encoding: UTF-8
# Installed before Main. Also renders the Chinese label in an English menu.
module FireAshZHTW
  FONT = "Microsoft JhengHei"
  NO_LINE_START = "，。、！？：；％）］｝〉》」』】〕〗〙〛…・·‧—,.!?:;%)]}”’"
  NO_LINE_END = "（［｛〈《「『【〔〖〘〚([{“‘"

  def self.cjk_boundary?(previous, current)
    return false unless previous && current
    return false if previous.match?(/\s/) || current.match?(/\s/)
    return false if NO_LINE_START.include?(current) || NO_LINE_END.include?(previous)
    previous.match?(/[\u3400-\u9fff]/) || current.match?(/[\u3400-\u9fff]/)
  end

  def self.active?
    return false unless defined?(Settings::LANGUAGES)
    return false unless defined?($PokemonSystem) && $PokemonSystem
    language = Settings::LANGUAGES[$PokemonSystem.language]
    language && language[1] == "traditional_chinese.dat"
  end

  def self.size(value)
    # Preview values; dialogue/menus still require in-game visual verification.
    value >= 25 ? (value * 0.8).round : value
  end

  def self.with_text_font(bitmap, text)
    previous = nil
    return yield if !text.is_a?(String) || text.ascii_only?
    sample = text.dup.force_encoding('UTF-8')
    return yield unless sample.valid_encoding? && sample.match?(/[\u3400-\u9fff]/)
    font = bitmap.font
    return yield if font.name == FONT && font.size < 25
    previous = [font.name, font.size]
    font.fire_ash_zhtw_name_set(FONT)
    font.fire_ash_zhtw_size_set(size(font.size))
    yield
  ensure
    if previous
      font.fire_ash_zhtw_name_set(previous[0])
      font.fire_ash_zhtw_size_set(previous[1])
    end
  end
end

class Bitmap
  alias_method :fire_ash_zhtw_draw_text, :draw_text
  alias_method :fire_ash_zhtw_text_size, :text_size

  def draw_text(*args)
    text = args.find { |arg| arg.is_a?(String) }
    FireAshZHTW.with_text_font(self, text) { fire_ash_zhtw_draw_text(*args) }
  end

  def text_size(*args)
    FireAshZHTW.with_text_font(self, args[0]) { fire_ash_zhtw_text_size(*args) }
  end
end

class Font
  alias_method :fire_ash_zhtw_initialize, :initialize
  alias_method :fire_ash_zhtw_name_set, :name=
  alias_method :fire_ash_zhtw_size_set, :size=

  def initialize(*args)
    fire_ash_zhtw_initialize(*args)
    if FireAshZHTW.active?
      self.fire_ash_zhtw_name_set(FireAshZHTW::FONT)
      self.fire_ash_zhtw_size_set(FireAshZHTW.size(size))
    end
  end

  def name=(value)
    self.fire_ash_zhtw_name_set(FireAshZHTW.active? ? FireAshZHTW::FONT : value)
  end

  def size=(value)
    self.fire_ash_zhtw_size_set(FireAshZHTW.active? ? FireAshZHTW.size(value) : value)
  end
end
