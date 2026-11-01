# encoding: UTF-8
# CPU-only display backend for the actual battle classes; never starts Game.exe.
$battle_ops=[]
$battle_bitmaps=[]
Color=Struct.new(:red,:green,:blue,:alpha) do
  def initialize(r,g,b,a=255); super(r,g,b,a); end
end
Rect=Struct.new(:x,:y,:width,:height) do
  def set(x,y,w,h); self.x=x; self.y=y; self.width=w; self.height=h; end
  def empty; set(0,0,0,0); end
end
class Font
  attr_accessor :name,:size,:bold,:italic,:color
  def initialize(*); @name='Power Green'; @size=29; @bold=false; @italic=false; @color=Color.new(80,80,88); end
  def self.exist?(*); true; end
end
class Bitmap
  attr_accessor :font
  attr_reader :width,:height,:audit_id,:path
  def initialize(a,b=nil)
    @audit_id=$battle_bitmaps.length; $battle_bitmaps << self
    @font=Font.new; @disposed=false
    if a.is_a?(String)
      @path=a.tr('\\','/').sub(/\.png\z/i,'')
      @width,@height=$battle_assets.fetch(@path).fetch('size')
      $battle_ops << ['load',@audit_id,@path]
    else
      @width=a; @height=b
      $battle_ops << ['new',@audit_id,@width,@height]
    end
  end
  def clone
    out=BitmapWrapper.new(width,height)
    out.instance_variable_set(:@path,@path)
    $battle_ops << ['copy',out.audit_id,@audit_id]
    out
  end
  def text_size(text)
    metric=$battle_metrics.fetch([font.name,font.size])
    Rect.new(0,0,text.each_char.sum { |c| metric[0].fetch(c) },metric[1])
  end
  def draw_text(*args)
    if args[0].is_a?(Rect)
      x,y,w,h=args.shift.to_a
    else
      x,y,w,h=args.shift(4)
    end
    text,align=args
    $battle_ops << ['text',audit_id,x,y,w,h,text,align||0,font.name,font.size,font.color.to_a]
  end
  def get_pixel(x,y)
    Color.new(*$battle_assets.fetch(@path).fetch('pixels').fetch("#{x},#{y}"))
  end
  def blt(x,y,other,rect,opacity=255); $battle_ops << ['blt',audit_id,x,y,other.audit_id,rect.to_a,opacity]; end
  def stretch_blt(rect,other,source,opacity=255); $battle_ops << ['stretch',audit_id,rect.to_a,other.audit_id,source.to_a,opacity]; end
  def fill_rect(x,y,w,h,color); $battle_ops << ['fill',audit_id,x,y,w,h,color.to_a]; end
  def clear; $battle_ops << ['clear',audit_id]; end
  def dispose; @disposed=true; end
  def disposed?; @disposed; end
end
class BitmapWrapper < Bitmap
  attr_reader :refcount
  def initialize(*args); super; @refcount=1; end
  def addRef; @refcount+=1; end
  def resetRef; @refcount=1; end
  def copy; out=clone; out.resetRef; out; end
  def dispose; return if disposed?; @refcount-=1; super if @refcount<=0; end
end
module RPG
  module Cache
    @cache={}
    def self.fromCache(key); b=@cache[key]; b if b && !b.disposed?; end
    def self.load_bitmap(folder,name,hue=0)
      key=folder+name
      b=fromCache(key)
      if b; b.addRef; return b; end
      @cache[key]=BitmapWrapper.new(key)
    end
  end
end
class AnimatedBitmap
  attr_reader :bitmap
  def initialize(path); @bitmap=RPG::Cache.load_bitmap('',path); end
  def width; bitmap.width; end
  def height; bitmap.height; end
  def dispose; bitmap.dispose; end
end
class SpriteWrapper
  attr_accessor :x,:y,:z,:visible,:bitmap,:src_rect,:opacity,:color,:zoom_x,:zoom_y
  def initialize(*)
    @x=@y=@z=0; @visible=true; @opacity=255; @src_rect=Rect.new(0,0,0,0); @disposed=false
  end
  def bitmap=(value)
    @bitmap=value; @src_rect=Rect.new(0,0,value.width,value.height) if value
  end
  def disposed?; @disposed; end
  def dispose; @disposed=true; end
end
class BitmapSprite < SpriteWrapper
  def initialize(w,h,viewport=nil); super(viewport); self.bitmap=BitmapWrapper.new(w,h); end
end
class IconSprite < SpriteWrapper
  def initialize(x,y,viewport=nil); super(viewport); @x=x; @y=y; end
  def setBitmap(path); self.bitmap=RPG::Cache.load_bitmap('',path); end
end
class Window_UnformattedTextPokemon < SpriteWrapper
  attr_accessor :text,:baseColor,:shadowColor,:windowskin,:back_opacity
  def self.newWithSize(*args); new; end
  def refresh; end
end
module Graphics
  def self.width; 512; end
  def self.height; 384; end
  def self.frame_rate; 40; end
end
module PokeBattle_SceneConstants
  MESSAGE_BASE_COLOR=Color.new(80,80,88)
  MESSAGE_SHADOW_COLOR=Color.new(160,160,168)
end
class Pokemon
  MAX_MOVES=4
end
module Settings
  LANGUAGES=[['English','english.dat'],['繁體中文','traditional_chinese.dat']]
  MAXRAID_SWITCH=0
end
class PokeBattle_FakeBattler; end
$game_switches=[]
$PokemonSystem=Struct.new(:language).new(1)
def pbSetSystemFont(b); b.font.name='Power Green'; b.font.size=29; end
def pbSetNarrowFont(b); b.font.name='Power Green Narrow'; b.font.size=29; end
def pbSetSmallFont(b); b.font.name='Power Green Small'; b.font.size=14; end
def pbBitmapName(path); path; end
def pbDisposeSpriteHash(hash); hash.each_value { |s| s.dispose }; end
def _INTL(key,*args)
  text=($PokemonSystem.language==1 ? $battle_ui.fetch(key,key) : key).dup.force_encoding('UTF-8')
  args.each_with_index { |arg,i| text.gsub!("{#{i+1}}",arg.to_s) }
  text
end
module GameData
  class Type
    def self.each; $battle_types.each { |t| yield t }; end
    def self.get(id); $battle_types.find { |t| t.id==id || t.id_number==id } || raise("Unknown type #{id}"); end
  end
end
BattleType=Struct.new(:id,:id_number,:english,:chinese) do
  def name; $PokemonSystem.language==1 ? chinese : english; end
end
BattleMove=Struct.new(:name,:type,:pp,:total_pp) do
  def short_name; name; end
end
class BattleBattler
  attr_accessor :index,:name,:displayGender,:level,:moves
  def initialize(index,name,gender,level)
    @index,@name,@displayGender,@level=index,name,gender,level
  end
  def pokemon; self; end
  def hp; 23; end
  def totalhp; 23; end
  def exp_fraction; 0.4; end
  def shiny?; index==0; end
  def mega?; false; end
  def primal?; false; end
  def ultra?; false; end
  def dynamax?; false; end
  def owned?; false; end
  def opposes?(*); index.odd?; end
  def status; :NONE; end
end
def battle_snapshot(sprites)
  sprites.each_with_index.filter_map do |s,i|
    next unless s.bitmap && s.visible
    [s.bitmap.audit_id,s.x,s.y,s.z,s.src_rect.to_a,i]
  end
end
'ready'
