# encoding: UTF-8
# Text the game shows without a language-table lookup: literals passed straight to message,
# command and draw calls, _INTL keys missing from the table, and English words passed as
# _INTL arguments. EXTRA_* constants come from translations/extra-text.json (builder).
# Chinese mode only; unknown text passes through unchanged.
module FireAshZHTW
  def self.extra(value)
    return value unless active? && value.is_a?(String) && value =~ /[A-Za-z]/
    key = display_string(value)
    hit = EXTRA_TEXT[key]
    return hit if hit
    EXTRA_PATTERNS.each do |pattern, template|
      match = pattern.match(key)
      return template.gsub(/\\(\d)/) { extra(match[$1.to_i]) } if match
    end
    return value unless EXTRA_FRAGMENTS.keys.any? { |en| key.include?(en) }
    EXTRA_FRAGMENTS.inject(key) { |text, (en, zh)| text.gsub(en, zh) }
  end

  # Same array back when nothing changed, so callers that keep mutating it still see updates.
  def self.extra_list(list)
    return list unless active? && list.is_a?(Array)
    out = list.map { |value| extra(value) }
    out == list ? list : out
  end

  def self.extra_args(arg)
    return arg unless active?
    arg = arg.dup
    arg[0] = EXTRA_TEXT.fetch(arg[0], arg[0]) if arg[0].is_a?(String)
    (1...arg.length).each { |i| arg[i] = extra(arg[i]) }
    arg
  end

  module ExtraCommands
    def initialize(commands = [], *rest)
      super(FireAshZHTW.extra_list(commands), *rest)
    end

    def commands=(value)
      super(FireAshZHTW.extra_list(value))
    end
  end

  module ExtraUnformattedText
    def initialize(text = "", *rest)
      super(FireAshZHTW.extra(text), *rest)
    end

    def text=(value)
      super(FireAshZHTW.extra(value))
    end
  end

  module ExtraAdvancedText
    def setText(value)
      super(FireAshZHTW.extra(value))
    end
  end
end

# Top-level helpers are aliased like the game's own hooks; nothing later redefines them.
alias fire_ash_extra_intl _INTL
def _INTL(*arg)
  fire_ash_extra_intl(*FireAshZHTW.extra_args(arg))
end

# An event that transfers the player keeps running, but command_101/102 look its text up in
# $game_map.map_id, the destination's table. Fall back to the event's own map when that misses.
module FireAshZHTW
  class << self; attr_accessor :event_map; end

  module EventMapText
    def execute_command
      previous = FireAshZHTW.event_map
      FireAshZHTW.event_map = @map_id
      super
    ensure
      FireAshZHTW.event_map = previous
    end
  end
end
Interpreter.prepend(FireAshZHTW::EventMapText)

alias fire_ash_extra_mapintl _MAPINTL
def _MAPINTL(mapid, *arg)
  arg = FireAshZHTW.extra_args(arg)
  origin = FireAshZHTW.event_map
  if FireAshZHTW.active? && origin && origin != mapid && arg[0].is_a?(String) &&
     MessageTypes.getFromMapHash(mapid, arg[0]).equal?(arg[0])   # returns the key itself on a miss
    mapid = origin
  end
  fire_ash_extra_mapintl(mapid, *arg)
end

alias fire_ash_extra_draw_text_positions pbDrawTextPositions
def pbDrawTextPositions(bitmap, textpos)
  if FireAshZHTW.active?
    textpos.each do |t|
      text = FireAshZHTW.extra(t[0])
      t[0] = text unless text.equal?(t[0])
    end
  end
  fire_ash_extra_draw_text_positions(bitmap, textpos)
end

alias fire_ash_extra_draw_shadow_text pbDrawShadowText
def pbDrawShadowText(bitmap, x, y, width, height, string, *rest)
  fire_ash_extra_draw_shadow_text(bitmap, x, y, width, height, FireAshZHTW.extra(string), *rest)
end

alias fire_ash_extra_draw_text_ex drawTextEx
def drawTextEx(bitmap, x, y, width, numlines, text, *rest)
  fire_ash_extra_draw_text_ex(bitmap, x, y, width, numlines, FireAshZHTW.extra(text), *rest)
end

# Prepended: some subclasses and plugins redefine these with bare defs.
Window_CommandPokemon.prepend(FireAshZHTW::ExtraCommands)
Window_UnformattedTextPokemon.prepend(FireAshZHTW::ExtraUnformattedText)
Window_AdvancedTextPokemon.prepend(FireAshZHTW::ExtraAdvancedText)
