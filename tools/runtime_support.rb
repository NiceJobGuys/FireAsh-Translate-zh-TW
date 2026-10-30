# encoding: UTF-8
# RUNTIME_TEXT is generated from translations/runtime-ui.json by the builder.
module FireAshZHTW
  def self.display_string(value)
    return value unless value.is_a?(String)
    utf8 = value.dup.force_encoding('UTF-8')
    utf8.valid_encoding? ? utf8 : value
  end

  def self.text(key)
    return key unless active?
    key = display_string(key)
    RUNTIME_TEXT.fetch(key) { _INTL(key) }
  end

  def self.intl(key, bindings, *args)
    replace = proc { |token| bindings.fetch(token, token).to_s }
    # Preserve the original lookup order in all other languages.
    return _INTL(key.gsub(/#\{[^{}]+\}/, &replace), *args) unless active?
    _INTL(display_string(key), *args.map { |value| display_string(value) }).gsub(/#\{[^{}]+\}/) do |token|
      display_string(bindings.fetch(token, token).to_s)
    end
  end
end

class SygnaBuff
  def display_name
    FireAshZHTW.text(@name)
  end

  def display_description
    @description && FireAshZHTW.text(@description)
  end
end
