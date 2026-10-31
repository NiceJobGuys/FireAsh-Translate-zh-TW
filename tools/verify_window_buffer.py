"""Replay actual dialog setText allocations, then clip raster ink to that bitmap."""
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
    ('empty', ''),
]


def verify(evaluate, put, original_window, patched_window, font_path, profile, sample_only=False):
    if not sample_only:
        f.json_write(f.ROOT/'text-buffer-validation.json',{'passed':False,'status':'running','profile':profile})
    pattern = r'  def setText\(value\).*?\n  end'
    original = re.search(pattern, original_window.replace('\r',''), re.S)[0]
    patched = re.search(pattern, patched_window.replace('\r',''), re.S)[0]
    evaluate('''class SpriteWindow_Base
  TEXTPADDING = 16 unless const_defined?(:TEXTPADDING)
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
    evaluate('class FireAshBufferProbe\n'+original+'\nend\n$buffer_old=FireAshBufferProbe.instance_method(:setText); "ready"')
    evaluate('class FireAshBufferProbe\n'+patched+'\nend\n$buffer_new=FireAshBufferProbe.instance_method(:setText); "ready"')
    font=ImageFont.truetype(str(font_path),24,index=0,layout_engine=ImageFont.Layout.BASIC)
    result=[]
    previews={}
    for language in (0,1):
        for letter in (False,True):
            for name,text in FIXTURES:
                put('$buffer_text',text)
                rendered={}
                for phase in ('old','new'):
                    evaluate(f'$PokemonSystem.language={language}; $buffer_probe=FireAshBufferProbe.new({str(letter).lower()}); '+
                             f'$buffer_{phase}.bind($buffer_probe).call($buffer_text); '+
                             '$buffer_probe.contents.clear_display_calls; '+
                             '$buffer_probe.fmtchars.each { |ch| drawSingleFormattedChar($buffer_probe.contents,ch) }; "ready"')
                    w,h=map(int,evaluate('$buffer_probe.dimensions.join(",")').split(','))
                    packed=evaluate('$buffer_probe.contents.display_calls.map { |c| [*c[1..4],c[5].unpack1("H*")].join("|") }.join(10.chr)')
                    calls=[(*map(int,row.split('|')[:4]),bytes.fromhex(row.split('|')[4]).decode()) for row in packed.splitlines()]
                    # The reference surface is deliberately taller; only the allocated
                    # window bitmap is clipped, as in the game's destination FBO.
                    reference=Image.new('L',(max(1,w),h+64))
                    draw=ImageDraw.Draw(reference)
                    for x,y,width,height,value in calls:
                        y+=int((height-sum(font.getmetrics()))/2)
                        draw.text((x,y),value,font=font,fill=255)
                    clipped=Image.new('L',reference.size)
                    clipped.paste(reference.crop((0,0,w,h)),(0,0))
                    lost=sum(v>0 for v in ImageChops.difference(reference,clipped).getdata())
                    rendered[phase]=(w,h,calls,lost,reference,clipped)
                old,new=rendered['old'],rendered['new']
                if language==1 and name=='screenshot' and not letter:
                    print('Dialog screenshot fixture:',profile,'old/new buffer heights',old[1],new[1],
                          'old/new missing ink pixels',old[3],new[3])
                assert old[0]==new[0] and old[2]==new[2], 'Glyph positions, pagination or calls changed'
                if language==0 or not text:
                    assert old[:4]==new[:4], 'English/empty window allocation changed'
                elif not sample_only:
                    assert new[1]==old[1]+4+max(sum(font.getmetrics())-32,0), 'Dialog buffer omitted offset/font overhang'
                    assert new[3]==0, (profile,name,'glyph pixels clipped',new[3])
                if language==1 and name=='screenshot' and not letter:
                    if profile=='noto' and not sample_only:
                        assert old[3]>0, 'Screenshot clipping was not reproduced'
                    previews={'before':old,'after':new}
                result.append({'language':language,'letter_by_letter':letter,'fixture':name,
                               'old_height':old[1],'new_height':new[1],'old_lost_pixels':old[3],
                               'new_lost_pixels':new[3]})
    if not sample_only:
        output=f.ARTIFACTS/'images/fire-ash/text-buffer-fix'
        output.mkdir(parents=True,exist_ok=True)
        from font_preview import save_preview
        for phase,values in previews.items():
            mask=values[5].crop((0,0,values[0],max(previews['before'][1],previews['after'][1])))
            canvas=Image.new('RGB',(480,80),(248,248,248))
            canvas.paste((48,80,200),(16,16),mask)
            save_preview(canvas,output/f'{profile}-{phase}-1x.png')
            save_preview(canvas.resize((1440,240),Image.Resampling.NEAREST),output/f'{profile}-{phase}-3x.png')
        f.json_write(f.ROOT/'text-buffer-validation.json',{
            'passed':True,'profile':profile,'cases':result,'glyph_positions_unchanged':True,
            'english_unchanged':True,'new_vertical_offset':0,'game_started':False,
            'scripts_sha256':f.digest((f.ARTIFACTS/'data/fire-ash-work/patched/Scripts.rxdata').read_bytes()),
            'language_sha256':f.digest((f.ARTIFACTS/'release/fire-ash-zh-tw-preview/Data/traditional_chinese.dat').read_bytes()),
            'font_sha256':f.digest(font_path.read_bytes()),
            'raster_model':'FreeType replay using mkxp vertical centering, clipped to native setText bitmap dimensions',
            'limitation':'No actual Game.exe/SDL rendering; user screenshot remains the real-game baseline.'})
    return len(result)
