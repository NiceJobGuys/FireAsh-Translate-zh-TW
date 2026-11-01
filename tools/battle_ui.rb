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
    'graphics/pictures/battle/cursor_shift','graphics/pictures/pokedex/icon_types',
    'graphics/pictures/naming/overlay_controls','graphics/pictures/naming/icon_mode'].freeze

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
    elsif ['graphics/pictures/types','graphics/pictures/pokedex/icon_types'].include?(path)
      dex = path.end_with?('/icon_types')
      width, step = dex ? [96,32] : [64,28]
      raise 'Unexpected type atlas dimensions' unless [bitmap.width,bitmap.height] == [width,step*19]
      GameData::Type.each do |type|
        row=type.id_number
        next unless row.is_a?(Integer) && row >= 0 && row < 19
        color=bitmap.get_pixel(dex ? 91 : 63,row*step+step/2)
        bitmap.fill_rect(dex ? 3 : 0,row*step+(dex ? 3 : 1),dex ? 90 : 64,26,color)
        dark=(color.red*299+color.green*587+color.blue*114)>150000
        ink=dark ? Color.new(32,32,32) : Color.new(248,248,248)
        fit_ui_text(bitmap,type.name,dex ? 4 : 2,row*step+2,width-(dex ? 8 : 4),step-4,ink,1,dex ? 27 : 14)
      end
    elsif path.include?('/naming/')
      selected=path.end_with?('/icon_mode')
      raise 'Unexpected naming atlas dimensions' unless [bitmap.width,bitmap.height] == (selected ? [240,44] : [480,206])
      labels=['大寫','小寫','重音','其他']
      labels.each_with_index do |label,i|
        x,y=selected ? [i*60+4,8] : [30+i*62,30]
        color=bitmap.get_pixel(x,selected ? 6 : 30)
        width=selected ? 52 : 56
        bitmap.fill_rect(x,y,width,30,color)
        fit_ui_text(bitmap,label,x,y,width,30,Color.new(48,48,48),1,14)
      end
      unless selected
        # Keep the original button borders and explain what the shortcuts actually do.
        [['切換字集',114,2,80,17,110,5],['刪除鍵',304,2,64,17,300,5],
         ['跳至確定',380,2,70,17,378,5],['刪除',304,30,64,32,304,30],
         ['確定',384,30,64,32,384,30]].each do |label,x,y,w,h,sx,sy|
          color=bitmap.get_pixel(sx,sy)
          bitmap.fill_rect(x,y<20 ? 4 : y,w,y<20 ? 13 : h,color)
          fit_ui_text(bitmap,label,x,y,w,h,Color.new(48,48,48),1,14)
        end
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

# ZUD also redefines FightMenuDisplay#refreshButtonNames; fit each move name inside its button.
module FireAshZHTW
  module FightMenuText
    def pbDrawTextPositions(bitmap,textpos)
      if FireAshZHTW.active? && @overlay && bitmap.equal?(@overlay.bitmap)
        textpos.reject! do |t|
          button=@buttons.find { |b| t[1]==b.x-self.x+b.src_rect.width/2 && t[2]==b.y-self.y+2 }
          next false unless button
          FireAshZHTW.fit_ui_text(bitmap,t[0],button.x-self.x+14,button.y-self.y+8,
            button.src_rect.width-28,FightMenuDisplay::BUTTON_HEIGHT-16,t[4],1)
          true
        end
      end
      super(bitmap,textpos)
    end
  end
end
FightMenuDisplay.prepend(FireAshZHTW::FightMenuText) if defined?(FightMenuDisplay)

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
