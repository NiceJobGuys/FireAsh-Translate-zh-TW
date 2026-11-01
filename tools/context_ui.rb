# encoding: UTF-8
# Context-specific labels must not replace the same words used as trainer names.
alias fire_ash_zhtw_month_name pbGetMonthName
def pbGetMonthName(month)
  return '５月' if FireAshZHTW.active? && month == 5
  fire_ash_zhtw_month_name(month)
end

alias fire_ash_zhtw_abbrev_month_name pbGetAbbrevMonthName
def pbGetAbbrevMonthName(month)
  return '５月' if FireAshZHTW.active? && month == 5
  fire_ash_zhtw_abbrev_month_name(month)
end

class PokemonStorage
  alias fire_ash_zhtw_wallpapers allWallpapers
  def allWallpapers
    labels = fire_ash_zhtw_wallpapers
    if FireAshZHTW.active?
      labels = labels.dup
      labels[13], labels[14], labels[16] = '機械', '格紋', '宇宙'
    end
    labels
  end
end

class GameData::BattleTerrain
  alias fire_ash_zhtw_name name
  def name
    return '薄霧' if FireAshZHTW.active? && @id == :Misty
    fire_ash_zhtw_name
  end
end

class GameData::Environment
  alias fire_ash_zhtw_name name
  def name
    return '宇宙' if FireAshZHTW.active? && @id == :Space
    fire_ash_zhtw_name
  end
end

module FireAshZHTW
  DIRECT_PLUGIN_MESSAGES = [
    'What would you like to do?',
    'No save file was found.',
    'Dynamax Pokémon have their own shadow sprite. The shadow size metric cannot be edited.',
    'This species has its own shadow sprite in Graphics/Pokemon/Shadow/. The shadow size metric cannot be edited.'
  ].freeze
end

# Plugins load later but call this existing helper. Translate only the reviewed prompts.
# The caller keeps its English options for case comparisons; pbMessage returns the same index.
alias fire_ash_zhtw_plugin_message pbMessage
def pbMessage(message, commands=nil, cmdIfCancel=0, skin=nil, defaultCmd=0, &block)
  if FireAshZHTW.active? && FireAshZHTW::DIRECT_PLUGIN_MESSAGES.include?(message)
    commands = commands.map { |label| _INTL(label) } if commands && message == 'What would you like to do?'
    message = _INTL(message)
  end
  fire_ash_zhtw_plugin_message(message, commands, cmdIfCancel, skin, defaultCmd, &block)
end
