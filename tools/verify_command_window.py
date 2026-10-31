"""Native command-window sizing, row/cursor painting and actual content clipping."""
import re
from PIL import Image, ImageDraw, ImageFont
import fire_ash as f

MENU_TEXT = ['整理盒子','領取寶可夢','寄放寶可夢','再見！','Pokémon gyjqp']


def method(code, name):
    return re.search(r'  def '+re.escape(name)+r'\b.*?\n  end',code,re.S)[0]


def class_code(code, name):
    return re.search(r'^class '+name+r' < .*?^end$',code,re.S|re.M)[0]


def verify(evaluate,put,original,patched,draw_code,sprite_code,font_path,profile,sample_only=False):
    report_path=f.ROOT/'command-window-validation.json'
    if not sample_only:f.json_write(report_path,{'passed':False,'status':'running'})
    original,patched=original.replace('\r',''),patched.replace('\r','')
    draw_code=draw_code.replace('\r','')
    new_shadow=re.search(r'^def pbDrawShadowText\(.*?^end$',draw_code,re.S|re.M)[0]
    old_shadow=new_shadow.replace('y += FireAshZHTW.row_text_offset(bitmap, height)','y += 4')
    assert old_shadow!=new_shadow
    evaluate(old_shadow+'\n$menu_old_shadow=method(:pbDrawShadowText); "ready"')
    evaluate(new_shadow+'\n$menu_new_shadow=method(:pbDrawShadowText); "ready"')
    drawable=class_code(original,'Window_DrawableCommand')
    selectable=class_code(original,'SpriteWindow_Selectable')
    clip=re.search(r'    if @width>trimWidth && @height>trimHeight.*?\n    end',sprite_code.replace('\r',''),re.S)[0]
    evaluate('''class Bitmap
  attr_accessor :width,:height
  def clear; clear_display_calls; end
  def dispose; end
  def blt(x,y,source,rect,opacity=255)
    @display_calls ||= []
    @display_calls << ['arrow',x,y,rect.width,rect.height,'',0,'',0,0,0,0,0]
  end
end
class BitmapWrapper < Bitmap
  def initialize(w,h); super(); self.width=w; self.height=h; end
end
def pbSetSystemFont(bitmap); bitmap.font.size=29; end
def pbDoEnsureBitmap(bitmap,w,h)
  bitmap ||= Bitmap.new
  bitmap.width=w; bitmap.height=h
  bitmap
end
module Graphics
  def self.height; 384; end
end
class FireAshMenuProbe
  attr_accessor :width,:height,:contents
  attr_reader :baseColor,:shadowColor,:index
  def configure(commands,columns,visible_rows,scroll,index)
    @commands=commands; @column_max=columns; @column_spacing=32; @row_height=32
    @virtualOy=scroll*32; @index=index; @starting=false
    @baseColor=Color.new(80,80,88,255); @shadowColor=Color.new(160,160,168,255)
    @selarrow=Struct.new(:bitmap).new(Struct.new(:width,:height).new(12,28))
    @contents=Bitmap.new; @contents.clear_display_calls
    resizeToFit(commands)
    self.height=[height,visible_rows*32+borderY].min if visible_rows
    @width=width; @height=height; @ox=0; @oy=0
    $menu_recorded=[]
    refresh
  end
  def columns; @column_max; end
  def columnSpacing; @column_spacing; end
  def rowHeight; @row_height; end
  def borderX; 32; end
  def borderY; 32; end
  def top_item; @virtualOy/32*@column_max; end
  def page_item_max; ((height-borderY)/32)*@column_max; end
  def itemCount; @commands.length; end
  def drawItem(index,count,rect)
    start=contents.display_calls.length
    native_drawItem(index,count,rect)
    contents.display_calls[start..].each { |call| $menu_recorded << [index,*call] }
  end
  def clip
    trimWidth=32; trimHeight=32
    @sprites={"contents"=>Struct.new(:src_rect).new(Rect.new(0,0,0,0))}
'''+clip+'''
    @sprites['contents'].src_rect.to_a
  end
'''+ '\n'.join(method(drawable,n) for n in ('getAutoDims','drawCursor','refresh'))+'\n'+method(selectable,'itemRect')+'\nend\n"ready"')
    font=ImageFont.truetype(str(font_path),24,index=0,layout_engine=ImageFont.Layout.BASIC)
    arrow=Image.open(f.GAME/'Graphics/Pictures/selarrow.png').convert('RGBA')
    assert arrow.size==(12,28) and arrow.getbbox()==(0,6,12,26)
    results=[]; previews={}
    scenarios=[('four',1,None,0,0),('last',1,None,0,3),('scrolled',1,2,2,3),('columns',2,None,0,3),('descenders',1,None,0,4)]
    for language in (0,1):
        for kind in ('plain','advanced','formatted'):
            labels=MENU_TEXT[:4] if language else ['Organize Boxes','Withdraw Pokémon','Deposit Pokémon','See ya!']
            if kind=='formatted':labels=['<c3=505058,A0A0A8>'+s+'</c3>' for s in labels]
            for scenario,columns,rows,scroll,index in scenarios:
                current=labels+([MENU_TEXT[4]] if scenario=='descenders' else [])
                put('$menu_labels_source','['+','.join(f.ruby_string(s) for s in current)+']')
                evaluate('$menu_labels=eval($menu_labels_source); "ready"')
                phases={}
                for phase,source in [('before',original),('after',patched)]:
                    code=class_code(source,'Window_CommandPokemon' if kind=='plain' else 'Window_AdvancedCommandPokemon')
                    draw=method(code,'drawItem').replace('def drawItem','def native_drawItem',1)
                    evaluate('class FireAshMenuProbe\n'+draw+'\n'+method(code,'resizeToFit')+'\nend\n'+
                        f'Object.send(:define_method,:pbDrawShadowText,$menu_{"old" if phase=="before" else "new"}_shadow); '+
                        f'$PokemonSystem.language={language}; $menu_probe=FireAshMenuProbe.new; '+
                        f'$menu_probe.configure($menu_labels,{columns},{rows if rows else "nil"},{scroll},{index}); "ready"')
                    _,_,w,h=map(int,evaluate('$menu_probe.clip.join(",")').split(','))
                    raw=evaluate('$menu_recorded.map { |c| [*c[0..5],c[6].unpack1("H*")].join("|") }.join(10.chr)')
                    calls=[(int(a),b,*map(int,(x,y,ww,hh)),bytes.fromhex(t).decode())
                           for a,b,x,y,ww,hh,t in (line.split('|') for line in raw.splitlines())]
                    canvas=Image.new('RGBA',(w,h),(248,248,248,255)); draw_image=ImageDraw.Draw(canvas)
                    lost=0; boxes=[]; arrow_boxes=[]
                    for idx,typ,x,y,ww,hh,value in calls:
                        if typ=='arrow':
                            canvas.alpha_composite(arrow,(x,y));arrow_boxes.append((idx,x,y+6,x+12,y+26));continue
                        py=y+int((hh-sum(font.getmetrics()))/2)
                        box=font.getbbox(value);box=(x+box[0],py+box[1],x+box[2],py+box[3])
                        boxes.append((idx,*box))
                        mask=Image.new('L',(w,h+64));ImageDraw.Draw(mask).text((x,py),value,font=font,fill=255)
                        # itemRect's historical inclusive end can visit one clipped row;
                        # count expected visible rows, not intentional hidden entries.
                        visible_rows=h//32
                        if scroll<=idx//columns<scroll+visible_rows:
                            lost+=sum(v>0 for v in mask.crop((0,h,w,h+64)).getdata())
                        draw_image.text((x,py),value,font=font,fill=(80,80,88,255))
                    phases[phase]=(w,h,calls,lost,boxes,arrow_boxes,canvas)
                before,after=phases['before'],phases['after']
                if language==0:assert before[:6]==after[:6],('English menu changed',kind,scenario)
                elif not sample_only:
                    assert after[3]==0,(kind,scenario,'menu ink cropped',after[3])
                    assert after[1]%32==0,('Menu height cuts its last row',kind,after[1])
                    if before[1]==after[1]:assert before[5]==after[5], 'Existing visible cursor position changed'
                    selected=[b for b in after[4] if b[0]==index]
                    marker=next(b for b in after[5] if b[0]==index)
                    cursor_width=(after[0]-(columns-1)*32)//columns
                    expected_x=index%columns*(cursor_width+32)
                    expected_y=(index//columns-scroll)*32
                    assert marker==(index,expected_x,expected_y+6,expected_x+12,expected_y+26),('Cursor not on selected row',marker)
                    mid=(min(b[2] for b in selected)+max(b[4] for b in selected))/2
                    assert abs(mid-(marker[2]+marker[4])/2)<=2,(kind,scenario,'cursor/text mismatch',mid,marker)
                if language==1 and kind=='plain' and scenario=='four':
                    if profile=='noto' and not sample_only:assert before[3]>0, 'PC menu clipping not reproduced'
                    previews=phases
                results.append({'language':language,'kind':kind,'scenario':scenario,'old_height':before[1],
                                'new_height':after[1],'old_lost_pixels':before[3],'new_lost_pixels':after[3]})
    evaluate('Object.send(:define_method,:pbDrawShadowText,$menu_new_shadow); "ready"')
    if not sample_only:
        from font_preview import save_preview
        out=f.ARTIFACTS/'images/fire-ash/command-window-fix';out.mkdir(parents=True,exist_ok=True)
        for phase,values in previews.items():
            content=values[6].convert('RGB');canvas=Image.new('RGB',(content.width+32,content.height+32),(220,192,128))
            ImageDraw.Draw(canvas).rectangle((4,4,canvas.width-5,canvas.height-5),fill=(248,248,248))
            canvas.paste(content,(16,16))
            save_preview(canvas,out/f'{profile}-{phase}-1x.png')
            save_preview(canvas.resize((canvas.width*2,canvas.height*2),Image.Resampling.NEAREST),out/f'{profile}-{phase}-2x.png')
        f.json_write(report_path,{'passed':True,'cases':results,'existing_visible_cursor_positions_unchanged':True,
            'all_selected_rows_have_cursor':True,
            'english_unchanged':True,'profile':profile,'game_started':False,
            'scripts_sha256':f.digest((f.ARTIFACTS/'data/fire-ash-work/patched/Scripts.rxdata').read_bytes()),
            'language_sha256':f.digest((f.ARTIFACTS/'release/fire-ash-zh-tw-preview/Data/traditional_chinese.dat').read_bytes()),
            'scope':'Native command sizing/rows/cursor/drawItem/contents clip; FreeType replay, not Game.exe capture.'})
    return len(results)
