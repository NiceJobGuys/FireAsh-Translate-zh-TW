# encoding: UTF-8
# Display-only rendering. Original textures, battler values and move data stay intact.
module FireAshZHTW
  GENDER_PIXELS = {
    '♂' => ['        ######','           ###','          ## #','         ##  #',
            '   #### ##    ','  ##  ###     ',' ##    ##     ',' #      #     ',
            ' #      #     ',' ##    ##     ','  ##  ##      ','   ####       ',
            '              ','              '],
    '♀' => ['    ####      ','   ##  ##     ','  ##    ##    ','  #      #    ',
            '  #      #    ','  ##    ##    ','   ##  ##     ','    ####      ',
            '     ##       ','     ##       ','   ######     ','   ######     ',
            '     ##       ','     ##       ']
  }.freeze
  COMMAND_LABELS = ['戰鬥','寶可夢','背包','逃跑','呼喚','投球','扔石頭','誘餌','投球','取消','加油','場地'].freeze
  LOCALIZED_BITMAPS = ['graphics/pictures/types','graphics/pictures/battle/cursor_command',
    'graphics/pictures/battle/cursor_mega','graphics/pictures/battle/cursor_dynamax',
    'graphics/pictures/battle/cursor_zmove','graphics/pictures/battle/cursor_ultra',
    'graphics/pictures/battle/cursor_shift'].freeze

  def self.draw_gender_icon(bitmap, symbol, x, y, color)
    @gender_icons ||= {}
    key=[symbol,color.red,color.green,color.blue,color.alpha]
    icon=@gender_icons[key]
    if !icon || icon.disposed?
      icon=BitmapWrapper.new(14,14)
      GENDER_PIXELS.fetch(symbol).each_with_index do |row,dy|
        row.to_enum(:scan, /#+/).each do
          run=Regexp.last_match
          icon.fill_rect(run.begin(0),dy,run[0].length,1,color)
        end
      end
      @gender_icons[key]=icon
    end
    bitmap.blt(x,y,icon,Rect.new(0,0,14,14))
  end

  def self.fit_ui_text(bitmap, text, x, y, width, height, color, align=0, max_size=27, outline=nil)
    font = bitmap.font
    previous = [font.name,font.size,font.bold,font.italic,font.color]
    font.fire_ash_zhtw_name_set(FONT)
    font.bold = font.italic = false
    sizes = max_size == 14 ? [14] : [27,14]
    label = display_string(text.to_s)
    sizes.each do |size|
      font.fire_ash_zhtw_size_set(size)
      break if bitmap.text_size(label).width <= width
    end
    if bitmap.text_size(label).width > width
      label = label.each_char.to_a
      label.pop while label.length > 0 && bitmap.text_size(label.join + '…').width > width
      label = label.join + '…'
    end
    # These are new bounded UI fields, not the legacy painter's +4px baseline.
    y += [0, (height - bitmap.text_size("Ag").height) / 2].min
    if outline
      font.color = outline
      [[-1,0],[1,0],[0,-1],[0,1]].each { |dx,dy| bitmap.draw_text(x+dx,y+dy,width,height,label,align) }
    end
    font.color = color
    bitmap.draw_text(x,y,width,height,label,align)
  ensure
    if previous
      font.fire_ash_zhtw_name_set(previous[0])
      font.fire_ash_zhtw_size_set(previous[1])
      font.bold,font.italic,font.color = previous[2],previous[3],previous[4]
    end
  end

  def self.localize_ui_bitmap(path, bitmap)
    if path == 'graphics/pictures/battle/cursor_command'
      raise 'Unexpected command atlas dimensions' unless bitmap.width == 260 && bitmap.height == 552
      COMMAND_LABELS.each_with_index do |label,row|
        2.times do |state|
          x=state*130; y=row*46
          # The clean column has the same horizontal colour bands as the label area.
          strip=BitmapWrapper.new(1,26)
          begin
            strip.blt(0,0,bitmap,Rect.new(x+12,y+10,1,26))
            bitmap.stretch_blt(Rect.new(x+14,y+10,102,26),strip,Rect.new(0,0,1,26))
          ensure
            strip.dispose
          end
          fit_ui_text(bitmap,label,x+8,y+7,114,32,Color.new(248,248,248),1,27,Color.new(48,48,48))
        end
      end
    elsif path == 'graphics/pictures/types'
      raise 'Unexpected type atlas dimensions' unless bitmap.width == 64 && bitmap.height == 532
      GameData::Type.each do |type|
        row=type.id_number
        next unless row.is_a?(Integer) && row >= 0 && row < bitmap.height/28
        color=bitmap.get_pixel(63,row*28+14)
        bitmap.fill_rect(0,row*28+1,64,26,color)
        dark=(color.red*299+color.green*587+color.blue*114)>150000
        ink=dark ? Color.new(32,32,32) : Color.new(248,248,248)
        fit_ui_text(bitmap,type.name,2,row*28+2,60,24,ink,1,14)
      end
    else
      shift=path.end_with?('/cursor_shift')
      raise 'Unexpected action atlas dimensions' unless [bitmap.width,bitmap.height] == (shift ? [196,46] : [150,92])
      (bitmap.height/46).times do |row|
        x=shift ? 14 : 54; width=shift ? 168 : 86; y=row*46
        strip=BitmapWrapper.new(1,26)
        begin
          strip.blt(0,0,bitmap,Rect.new(x-2,y+10,1,26))
          bitmap.stretch_blt(Rect.new(x,y+10,width,26),strip,Rect.new(0,0,1,26))
        ensure
          strip.dispose
        end
        fit_ui_text(bitmap,shift ? '特殊切換' : '行動',x,y+7,width,32,Color.new(248,248,248),1,27,Color.new(48,48,48))
      end
    end
  end
end

# ZUD Plugin redefines PokemonDataBox#refresh after all Scripts load and still draws a font
# ♂/♀ over Lv.; a prepended hook outranks that later definition.
module FireAshZHTW
  module DataBoxText
    def pbDrawTextPositions(bitmap,textpos)
      if FireAshZHTW.active? && bitmap.equal?(self.bitmap)
        # In place: ZUD passes the same array again after pushing the gender symbol.
        textpos.reject! do |t|
          if t[0]=='♂' || t[0]=='♀'
            FireAshZHTW.draw_gender_icon(bitmap,t[0],@spriteBaseX+118,16,t[4])
            true
          elsif t[0]==@battler.name && t[4].equal?(PokemonDataBox::NAME_BASE_COLOR)
            FireAshZHTW.fit_ui_text(bitmap,t[0],@spriteBaseX+8,10,104,28,t[4])
            true
          end
        end
      end
      super(bitmap,textpos)
    end
  end
end
PokemonDataBox.prepend(FireAshZHTW::DataBoxText) if defined?(PokemonDataBox)

# Cache localized copies under separate keys so English and live original sprites
# never see a modified shared texture. The game's normal refcount/clear owns them.
if defined?(RPG::Cache)
  module RPG::Cache
    class << self
      alias_method :fire_ash_zhtw_original_load_bitmap, :load_bitmap
      def load_bitmap(folder,filename,hue=0)
        path=(folder+filename).tr('\\','/').sub(/\.png\z/i,'').downcase
        return fire_ash_zhtw_original_load_bitmap(folder,filename,hue) unless FireAshZHTW.active? && FireAshZHTW::LOCALIZED_BITMAPS.include?(path)
        key=['FireAshZHTW',path,hue]
        cached=fromCache(key)
        if cached
          cached.addRef
          return cached
        end
        original=fire_ash_zhtw_original_load_bitmap(folder,filename,hue)
        copy=nil
        begin
          copy=original.copy
          FireAshZHTW.localize_ui_bitmap(path,copy)
          @cache[key]=copy
          copy
        rescue
          copy.dispose if copy && !copy.disposed?
          raise
        ensure
          original.dispose
        end
      end
    end
  end
end
