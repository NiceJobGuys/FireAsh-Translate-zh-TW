"""Replay dialog allocations and the real contents src_rect, including scrolling."""
import json
import re

from PIL import Image, ImageChops, ImageDraw, ImageFont

import fire_ash as f

FIXTURES = [
    ('screenshot', '大木博士是寶可夢研究的頂尖專家。'),
    ('two-lines', '大木博士是寶可夢研究的頂尖專家。\n寶可夢的世界充滿驚奇與夢想。'),
    ('three-lines', '大木博士。\n寶可夢研究。\n家夢寶是專。'),
    ('wrap', '大木博士是寶可夢研究的頂尖專家。這個世界充滿了寶可夢，和夥伴一起探索吧！'),
    ('mixed', '寶可夢 HP 123 / 456，研究家！'),
    ('descenders', 'Pokémon gyjqp，寶可夢！'),
    ('second-screenshot', '大木博士：Ash，你遲到了。最初的夥伴\n寶可夢都被領走了。……其實還有一'),
    ('empty', ''),
]


def verify(evaluate, put, original_window, patched_window, font_path, profile, sprite_window, sample_only=False):
    if not sample_only:
        f.json_write(f.ROOT/'text-buffer-validation.json',{'passed':False,'status':'running','profile':profile})
    pattern = r'  def setText\(value\).*?\n  end'
    original = re.search(pattern, original_window.replace('\r',''), re.S)[0]
    patched = re.search(pattern, patched_window.replace('\r',''), re.S)[0]
    evaluate('''class SpriteWindow_Base
end
class FireAshBufferProbe
  attr_reader :contents, :fmtchars
  def initialize(letter)
    @letterbyletter=letter
    @contents=Bitmap.new
    @contents.font.color=Color.new(48,80,200,255)
    @baseColor=@contents.font.color
    @shadowColor=Color.new(160,160,168,255)
  end
  def width; 480; end
  def height; 96; end
  def borderX; 32; end
  def borderY; 32; end
  def shadowctag(*); ''; end
  def unformattedTextLength(value); value.length; end
  def stopPause; end
  def refresh; end
  def dimensions; [@bitmapwidth,@bitmapheight]; end
end
"ready"
''')
    padding=int(re.search(r'TEXTPADDING\s*=\s*(\d+)',sprite_window)[1])
    evaluate('SpriteWindow_Base.send(:remove_const,:TEXTPADDING) if SpriteWindow_Base.const_defined?(:TEXTPADDING); '+
             f'SpriteWindow_Base.const_set(:TEXTPADDING,{padding}); "ready"')
    evaluate('class FireAshBufferProbe\n'+original+'\nend\n$buffer_old=FireAshBufferProbe.instance_method(:setText); "ready"')
    evaluate('class FireAshBufferProbe\n'+patched+'\nend\n$buffer_new=FireAshBufferProbe.instance_method(:setText); "ready"')
    clip_block=re.search(r'    if @width>trimWidth && @height>trimHeight.*?\n    end',sprite_window.replace('\r',''),re.S)[0]
    evaluate('''class Rect
  def set(x,y,w,h); self.x=x; self.y=y; self.width=w; self.height=h; end
end
class FireAshBufferProbe
  def clip_rectangle(scroll)
    @width=480; @height=96; @ox=0; @oy=scroll
    trimWidth=32; trimHeight=32
    @sprites={"contents"=>Struct.new(:src_rect).new(Rect.new(0,0,0,0))}
'''+clip_block+'''
    @sprites["contents"].src_rect.to_a
  end
end
"ready"
''')
    font=ImageFont.truetype(str(font_path),24,index=0,layout_engine=ImageFont.Layout.BASIC)
    result=[]
    previews={}
    page_previews={}
    for language in (0,1):
        for letter in (False,True):
            for name,text in FIXTURES:
                put('$buffer_text',text)
                rendered={}
                viewport_results={}
                for phase in ('old','new'):
                    evaluate(f'$PokemonSystem.language={language}; $buffer_probe=FireAshBufferProbe.new({str(letter).lower()}); '+
                             f'$buffer_{phase}.bind($buffer_probe).call($buffer_text); '+
                             '$buffer_probe.contents.clear_display_calls; '+
                             '$buffer_probe.fmtchars.each { |ch| drawSingleFormattedChar($buffer_probe.contents,ch) }; "ready"')
                    w,h=map(int,evaluate('$buffer_probe.dimensions.join(",")').split(','))
                    packed=evaluate('$buffer_probe.contents.display_calls.map { |c| [*c[1..4],c[5].unpack1("H*")].join("|") }.join(10.chr)')
                    calls=[(*map(int,row.split('|')[:4]),bytes.fromhex(row.split('|')[4]).decode()) for row in packed.splitlines()]
                    # Check both independent clipping layers: bitmap and contents sprite.
                    reference=Image.new('L',(max(1,w),h+64))
                    draw=ImageDraw.Draw(reference)
                    for x,y,width,height,value in calls:
                        y+=int((height-sum(font.getmetrics()))/2)
                        draw.text((x,y),value,font=font,fill=255)
                    clipped=Image.new('L',reference.size)
                    clipped.paste(reference.crop((0,0,w,h)),(0,0))
                    lost=sum(v>0 for v in ImageChops.difference(reference,clipped).getdata())
                    viewport_losses=[]
                    first_y=calls[0][1] if calls else 0
                    for scroll in (0,32):
                        _,_,vw,vh=map(int,evaluate(f'$buffer_probe.clip_rectangle({scroll}).join(",")').split(','))
                        assert (vw,vh)==(448,64), 'Unexpected native content viewport'
                        page=Image.new('L',reference.size)
                        page_draw=ImageDraw.Draw(page)
                        for x,y,width,height,value in calls:
                            row=(y-first_y)//32
                            if scroll//32 <= row < scroll//32+2:
                                page_draw.text((x,y+int((height-sum(font.getmetrics()))/2)),value,font=font,fill=255)
                        visible=Image.new('L',reference.size)
                        bottom=min(scroll+vh,h)
                        if bottom>scroll:
                            visible.paste(clipped.crop((0,scroll,w,bottom)),(0,scroll))
                        viewport_losses.append(sum(v>0 for v in ImageChops.difference(page,visible).getdata()))
                    rendered[phase]=(w,h,calls,lost,reference,clipped)
                    viewport_results[phase]=viewport_losses
                    if phase=='new' and language==1 and not sample_only:
                        assert max(viewport_losses)==0,(name,'visible content viewport still clips',viewport_losses)
                old,new=rendered['old'],rendered['new']
                if language==1 and name=='screenshot' and not letter:
                    print('Dialog screenshot fixture:',profile,'old/new buffer heights',old[1],new[1],
                          'old/new missing ink pixels',old[3],new[3])
                assert old[0]==new[0], 'Horizontal allocation changed'
                assert [(x,w,h,t) for x,y,w,h,t in old[2]]==[(x,w,h,t) for x,y,w,h,t in new[2]], 'Horizontal layout or glyph calls changed'
                if language==0 or not text:
                    assert old[:4]==new[:4], 'English/empty window allocation changed'
                elif not sample_only:
                    shift=min(4,(32-sum(font.getmetrics()))//2)-4
                    assert new[1]==old[1], 'Row allocation or pagination changed'
                    assert all(n[1]==o[1]+shift for o,n in zip(old[2],new[2])), 'Inconsistent text baseline adjustment'
                    assert new[3]==0, (profile,name,'glyph pixels clipped',new[3])
                if language==1 and name=='screenshot' and not letter:
                    if profile=='noto' and not sample_only:
                        assert old[3]>0, 'Screenshot clipping was not reproduced'
                    previews={'before':old,'after':new}
                if language==1 and name=='second-screenshot' and not letter:
                    page_previews={'before':old,'after':new}
                result.append({'language':language,'letter_by_letter':letter,'fixture':name,
                               'old_height':old[1],'new_height':new[1],'old_lost_pixels':old[3],
                               'new_lost_pixels':new[3],'old_viewport_lost_pixels':viewport_results['old'],
                               'new_viewport_lost_pixels':viewport_results['new']})
    if not sample_only:
        # Keep full-size embedded icons inside their row when text needs a negative offset.
        evaluate('$saved_buffer_formatter=method(:getFormattedText); '+
                 'Object.send(:define_method,:getFormattedText) { |*args| [["icon",0,(32-$buffer_icon_size)/2,$buffer_icon_size,32,true]] }; "ready"')
        try:
            for language in (0,1):
                for letter in (False,True):
                    for size in (24,32):
                        y=int(evaluate(f'$PokemonSystem.language={language}; $buffer_icon_size={size}; '+
                              f'$buffer_probe=FireAshBufferProbe.new({str(letter).lower()}); '+
                              '$buffer_new.bind($buffer_probe).call("icon"); $buffer_probe.fmtchars[0][2].to_s'))
                        assert y==(32-size)//2+(4 if language==0 else max(0,min(4,(32-sum(font.getmetrics()))//2)))
                        if language==1: assert 0<=y and y+size<=32
        finally:
            evaluate('Object.send(:define_method,:getFormattedText,$saved_buffer_formatter); "ready"')
        language_data=f.loads((f.ARTIFACTS/'release/fire-ash-zh-tw-preview/Data/traditional_chinese.dat').read_bytes())
        used={c for _,_,_,value in f.records(language_data) for c in f.analyze_message(value)[1] if ord(c)>=32}
        origin=min(4,(32-sum(font.getmetrics()))//2)+int((32-sum(font.getmetrics()))/2)
        for char in used:
            if font.getmask(char).getbbox():
                box=font.getbbox(char)
                assert 0<=origin+box[1] and origin+box[3]<=32,('Glyph leaves its visible line',char,box,origin)
        output=f.ARTIFACTS/'images/fire-ash/text-buffer-fix'
        output.mkdir(parents=True,exist_ok=True)
        from font_preview import save_preview
        for phase,values in previews.items():
            mask=values[5].crop((0,0,values[0],max(previews['before'][1],previews['after'][1])))
            canvas=Image.new('RGB',(480,80),(248,248,248))
            canvas.paste((48,80,200),(16,16),mask)
            save_preview(canvas,output/f'{profile}-{phase}-1x.png')
            save_preview(canvas.resize((1440,240),Image.Resampling.NEAREST),output/f'{profile}-{phase}-3x.png')
        for phase,values in page_previews.items():
            mask=values[5].crop((0,0,min(values[0],448),64))
            canvas=Image.new('RGB',(480,96),(80,80,88))
            ImageDraw.Draw(canvas).rectangle((4,4,475,91),fill=(248,248,248))
            canvas.paste((48,80,200),(16,16),mask)
            save_preview(canvas,output/f'{profile}-two-lines-{phase}-1x.png')
            save_preview(canvas.resize((1440,288),Image.Resampling.NEAREST),output/f'{profile}-two-lines-{phase}-3x.png')
        f.json_write(f.ROOT/'text-buffer-validation.json',{
            'passed':True,'profile':profile,'cases':result,'horizontal_positions_unchanged':True,
            'english_unchanged':True,'dialog_y_offset':min(4,(32-sum(font.getmetrics()))//2),
            'viewport_height':64,'scroll_offsets_checked':[0,32],'game_started':False,
            'visible_character_line_bounds_checked':len(used),
            'icon_position_cases_checked':8,
            'scripts_sha256':f.digest((f.ARTIFACTS/'data/fire-ash-work/patched/Scripts.rxdata').read_bytes()),
            'language_sha256':f.digest((f.ARTIFACTS/'release/fire-ash-zh-tw-preview/Data/traditional_chinese.dat').read_bytes()),
            'font_sha256':f.digest(font_path.read_bytes()),
            'raster_model':'FreeType replay, native setText dimensions AND actual SpriteWindow contents src_rect clipping',
            'limitation':'No actual Game.exe/SDL rendering; user screenshot remains the real-game baseline.'})
    return len(result)
