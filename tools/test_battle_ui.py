"""Render actual battle UI classes through a CPU bitmap/sprite trace backend."""
import json
import argparse
import re
import sys
import zlib
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import fire_ash as f
from ruby_vm import RubyVM
from font_preview import save_preview

sys.stdout.reconfigure(encoding='utf-8')
REPORT=f.ROOT/'battle-ui-validation.json'
OUT=f.ARTIFACTS/'images/fire-ash/battle-ui-fix'


def literal(value):
    if isinstance(value,str):return f.ruby_string(value)
    if isinstance(value,list):return '['+','.join(literal(x) for x in value)+']'
    if isinstance(value,dict):return '{'+','.join(literal(k)+'=>'+literal(v) for k,v in value.items())+'}'
    return str(value)


def zud_databox_refresh():
    # The game loads plugins after Scripts; ZUD's PokemonDataBox#refresh is the one that runs.
    plugins=f.loads((f.GAME/'Data/PluginScripts.rxdata').read_bytes())
    code=next(zlib.decompress(s[1]).decode('utf-8') for p in plugins if f.text(p[0])=='ZUD Plugin'
              for s in p[2] if f.text(s[0])=='[004] Battle Core/UI Databox.rb').replace('\r','')
    return 'class PokemonDataBox\n'+re.search(r'^  def refresh\n.*?^  end$',code,re.S|re.M)[0]+'\nend\n"ready"'


def main(archive=None):
    archive=archive or f.ARTIFACTS/'data/fire-ash-work/patched/Scripts.rxdata'
    scripts={f.text(r[1]):zlib.decompress(r[2]).decode('utf-8').replace('\r','') for r in f.loads(archive.read_bytes())}
    data=f.loads((f.ARTIFACTS/'release/fire-ash-zh-tw-preview/Data/traditional_chinese.dat').read_bytes())
    ui=dict(zip(*f.loads(data[24]._dump())))
    assets={}; originals={}
    paths=list((f.GAME/'Graphics/Pictures/Battle').glob('*.png'))+[f.GAME/'Graphics/Pictures/types.png',f.GAME/'Graphics/Pictures/shiny.png']
    for p in paths:
        key=p.relative_to(f.GAME).with_suffix('').as_posix();im=Image.open(p).convert('RGBA');originals[key]=im
        points={(10,y) for y in range(im.height)}|{(63,y) for y in range(im.height) if im.width>63}
        assets[key]={'size':list(im.size),'pixels':{f'{x},{y}':list(im.getpixel((x,y))) for x,y in points if x<im.width}}
    source_hashes={str(p):f.digest(p.read_bytes()) for p in paths}
    names=['蚊香蝌蚪','PIKA','超級無敵長名字測試寶可夢','電擊','十萬伏特','高速移動','電光一閃','超極巨萬雷轟頂','特殊切換','行動']
    chars=set(''.join(v for _,_,_,v in f.records(data))+''.join(names)+(f.ROOT/'tools/battle_ui.rb').read_text(encoding='utf-8'))
    fonts={}; metrics={}
    coverage=json.loads((f.ROOT/'coverage.json').read_text(encoding='utf-8'))
    family=coverage['font']['family']
    for fam,path in [(family,f.staged_font_path(coverage['font']['profile'])),('Power Green',f.GAME/'Fonts/power green.ttf'),
                     ('Power Green Narrow',f.GAME/'Fonts/power green narrow.ttf'),('Power Green Small',f.GAME/'Fonts/power green small.ttf')]:
        for size in range(10,30):  # name shrink loops step below the pixel sizes
            font=ImageFont.truetype(str(path),int(size*0.9),layout_engine=ImageFont.Layout.BASIC)
            fonts[(fam,size)]=font
            metrics[(fam,size)]=[{c:int(font.getlength(c)) for c in chars},sum(font.getmetrics())]
    vm=RubyVM(f.GAME)
    vm.evaluate('$battle_assets='+literal(assets)+'; "ready"')
    vm.evaluate('$battle_metrics={'+','.join(literal(list(k))+'=>'+literal(v) for k,v in metrics.items())+'}; "ready"')
    vm.evaluate('$battle_ui='+literal({f.text(k):f.text(v) for k,v in ui.items()})+'; "ready"')
    vm.evaluate((f.ROOT/'tools/battle_ui_probe.rb').read_text(encoding='utf-8'))
    types=f.loads((f.GAME/'Data/types.dat').read_bytes())
    rows=[v.attributes for k,v in types.items() if isinstance(k,int)]
    constructors=[f'BattleType.new({f.ruby_string(str(t["@id"]).lstrip(":"))}.to_sym,{t["@id_number"]},{f.ruby_string(str(t["@real_name"]))},{f.ruby_string(str(data[12][t["@id_number"]]))})' for t in rows]
    vm.evaluate('$battle_types=['+','.join(constructors)+']; "ready"')
    vm.evaluate(scripts['FireAsh_ZHTW_Font']+'\n"ready"')
    vm.evaluate((f.ROOT/'tools/runtime_support.rb').read_text(encoding='utf-8')+'\n"ready"')
    # Game order: SceneElements, then FireAsh_ZHTW_Runtime, then plugins.
    box=re.search(r'^class PokemonDataBox < .*?^end$',scripts['PokeBattle_SceneElements'],re.S|re.M)[0]
    vm.evaluate(box+'\n"ready"')
    # Only the new UI support is evaluated here; runtime dialogue tests cover its other siblings.
    vm.evaluate((f.ROOT/'tools/battle_ui.rb').read_text(encoding='utf-8')+'\n"ready"')
    vm.evaluate(zud_databox_refresh())
    vm.evaluate(scripts['DrawText']+'\n"ready"')
    vm.evaluate(scripts['PokeBattle_SceneMenus']+'\n"ready"')
    frames=[]; english_specs=[]
    def snap(name,code):
        if name.split('-')[1]=='0':english_specs.append((name,code))
        vm.evaluate(code+'; "ready"')
        raw=bytes.fromhex(vm.evaluate('Marshal.dump($battle_ops).unpack1("H*")'))
        ops=f.loads(raw);vm.evaluate('$battle_ops=[]; "ready"')
        sprites=f.loads(bytes.fromhex(vm.evaluate('Marshal.dump($battle_snapshot).unpack1("H*")')))
        frames.append((name,ops,sprites))
    for lang in (0,1):
        for mode in range(5):
            for selected in range(4):
                snap(f'command-{lang}-{mode}-{selected}',f'$PokemonSystem.language={lang}; $scene=CommandMenuDisplay.new(nil,100); '+
                     f'$scene.setIndexAndMode({selected},{mode}); $scene.visible=true; '+
                     '$battle_snapshot=battle_snapshot($scene.instance_variable_get(:@sprites).values)')
        for selected in range(4):
            for pp,total in ((0,15),(14,15),(30,30),(99,99)):
                moves=[f'BattleMove.new({f.ruby_string(n)},:{t},{pp},{total})' for n,t in
                       zip(['電擊','十萬伏特','高速移動','電光一閃'],['ELECTRIC','ELECTRIC','PSYCHIC','NORMAL'])]
                snap(f'fight-{lang}-{selected}-{pp}',f'$PokemonSystem.language={lang}; $scene=FightMenuDisplay.new(nil,100); '+
                     '$b=BattleBattler.new(0,"PIKA",0,5); $b.moves=['+','.join(moves)+']; '+
                     f'$scene.battler=$b; $scene.index={selected}; $scene.visible=true; '+
                     '$battle_snapshot=battle_snapshot($scene.instance_variable_get(:@sprites).values)')
        for index in (0,1):
            for gender in (0,1,2):
                for level in (2,100):
                    name=names[0] if index else 'PIKA'
                    snap(f'box-{lang}-{index}-{gender}-{level}',f'$PokemonSystem.language={lang}; '+
                         f'$box=PokemonDataBox.new(BattleBattler.new({index},{f.ruby_string(name)},{gender},{level}),1,nil); '+
                         '$box.x=0; $box.y=0; $box.visible=true; '+
                         '$battle_snapshot=battle_snapshot([$box,*$box.instance_variable_get(:@sprites).values])')
    # Cache must isolate English/shared source, share localized copies, and release failed paints.
    print(vm.evaluate('''$PokemonSystem.language=0
o=RPG::Cache.load_bitmap('Graphics/Pictures/','types')
$PokemonSystem.language=1
c=RPG::Cache.load_bitmap('Graphics/Pictures/','types')
d=RPG::Cache.load_bitmap('Graphics/Pictures/','types')
raise 'Shared texture mutated/uncached' if o.equal?(c) || !c.equal?(d)
$PokemonSystem.language=0
e=RPG::Cache.load_bitmap('Graphics/Pictures/','types')
raise 'English cache changed' unless e.equal?(o)
c.dispose; d.dispose; o.dispose; e.dispose
'PASS: localized texture cache isolation/refcount and English reuse'
'''))
    print(vm.evaluate('''$PokemonSystem.language=1
source=RPG::Cache.fire_ash_zhtw_original_load_bitmap('Graphics/Pictures/','types')
refs=source.refcount
saved=FireAshZHTW.method(:localize_ui_bitmap)
FireAshZHTW.define_singleton_method(:localize_ui_bitmap) { |*args| raise 'paint failure fixture' }
begin
  RPG::Cache.load_bitmap('Graphics/Pictures/','types',777)
  raise 'Failure fixture did not throw'
rescue RuntimeError => e
  raise unless e.message=='paint failure fixture'
ensure
  FireAshZHTW.define_singleton_method(:localize_ui_bitmap,saved)
end
raise 'Failed copy leaked' unless $battle_bitmaps.last.disposed? && source.refcount==refs
source.dispose
b=BitmapWrapper.new(100,32)
before=[b.font.name,b.font.size,b.font.bold,b.font.italic,b.font.color]
b.define_singleton_method(:draw_text) { |*args| raise 'draw failure fixture' }
begin
  FireAshZHTW.fit_ui_text(b,'測試',0,0,80,32,Color.new(0,0,0))
rescue RuntimeError => e
  raise unless e.message=='draw failure fixture'
end
raise 'Font state leaked' unless before==[b.font.name,b.font.size,b.font.bold,b.font.italic,b.font.color]
'PASS: failed paints release copies and fitted text restores font state'
'''))
    for asset in ['types','Battle/cursor_mega','Battle/cursor_dynamax','Battle/cursor_zmove','Battle/cursor_ultra','Battle/cursor_shift']:
        snap('atlas-1-'+asset.replace('/','-'), '$PokemonSystem.language=1; $s=SpriteWrapper.new; '+
             '$s.bitmap=RPG::Cache.load_bitmap("Graphics/Pictures/",'+f.ruby_string(asset)+'); $battle_snapshot=battle_snapshot([$s])')
    for index in (0,1):
        snap(f'longname-1-{index}',f'$PokemonSystem.language=1; $box=PokemonDataBox.new(BattleBattler.new({index},'+
             f.ruby_string(names[2])+',1,100),1,nil); $box.x=0; $box.y=0; $box.visible=true; '+
             '$battle_snapshot=battle_snapshot([$box,*$box.instance_variable_get(:@sprites).values])')
    originals_code={f.text(r[1]):zlib.decompress(r[2]).decode('utf-8').replace('\r','') for r in
                    f.loads((f.ARTIFACTS/'data/fire-ash-work/original-baseline/Data/Scripts.rxdata').read_bytes())}
    vm.evaluate('[:CommandMenuDisplay,:FightMenuDisplay,:TargetMenuDisplay,:BattleMenuBase,:PokemonDataBox].each { |n| Object.send(:remove_const,n) }; "ready"')
    vm.evaluate(originals_code['PokeBattle_SceneMenus']+'\n"ready"')
    vm.evaluate(re.search(r'^class PokemonDataBox < .*?^end$',originals_code['PokeBattle_SceneElements'],re.S|re.M)[0]+'\n"ready"')
    vm.evaluate(zud_databox_refresh())
    for name,code in list(english_specs):snap('original-'+name,code)
    pane=originals['Graphics/Pictures/Battle/overlay_fight']
    white=[x for x in range(384,512) if pane.getpixel((x,60))==(248,248,248,255)]
    assert (min(white),max(white)+1)==(402,494), 'PP pane interior changed'
    images={}; text_boxes=[]; snapshots={}; all_text=[]; loaded={}; gender_checks=0
    for name,ops,sprites in frames:
        gender_icons=[]
        for op in ops:
            kind,*a=op
            if kind=='load':images[a[0]]=originals[a[1]].copy();loaded[a[0]]=a[1]
            elif kind=='new':images[a[0]]=Image.new('RGBA',(a[1],a[2]))
            elif kind=='copy':images[a[0]]=images[a[1]].copy()
            elif kind=='clear':images[a[0]].paste((0,0,0,0),(0,0,*images[a[0]].size))
            elif kind=='fill':
                ident,x,y,w,h,color=a;ImageDraw.Draw(images[ident]).rectangle((x,y,x+w-1,y+h-1),fill=tuple(color))
            elif kind in ('blt','stretch'):
                if kind=='blt':ident,x,y,source,rect,opacity=a;w,h=rect[2:]
                else:ident,dst,source,rect,opacity=a;x,y,w,h=dst
                sx,sy,sw,sh=rect
                if w<=0 or h<=0:continue
                crop=images[source].crop((sx,sy,sx+sw,sy+sh)).resize((int(w),int(h)),Image.Resampling.NEAREST)
                if kind=='blt' and (name.startswith('box-1') or name.startswith('longname-1')) and images[source].size==(14,14):
                    base=16 if name.split('-')[2]=='1' else 34
                    assert (x,y,w,h)==(base+118,16,14,14)
                    assert x+w<=base+140-8, 'Gender icon overlaps level icon'
                    gender_icons.append((x,y,crop.copy()))
                if opacity!=255:crop.putalpha(crop.getchannel('A').point(lambda v:v*opacity//255))
                images[ident].alpha_composite(crop,(int(x),int(y)))
            elif kind=='text':
                ident,x,y,w,h,text,align,fam,size,color=a;text=f.text(text);fam=f.text(fam)
                font=fonts[(fam,size)];tw=font.getlength(text)
                if name.split('-')[1]=='1':assert tw<=w,(name,'horizontal squeeze',text,tw,w)
                px=x+max(0,int((w-tw)/(2 if align==1 else 1))) if align else x
                py=y+int((h-sum(font.getmetrics()))/2)
                box=ImageDraw.Draw(images[ident]).textbbox((px,py),text,font=font)
                if name.split('-')[1]=='1':
                    assert box[0]>=0 and box[1]>=0 and box[2]<=images[ident].width and box[3]<=images[ident].height,(name,text,box,images[ident].size)
                ImageDraw.Draw(images[ident]).text((px,py),text,font=font,fill=tuple(color))
                text_boxes.append((name,ident,text,box));all_text.append(text)
            else:raise AssertionError(kind)
        canvas=Image.new('RGBA',(512,384),(216,232,208,255))
        for ident,x,y,z,rect,order in sorted(sprites,key=lambda s:(s[3],s[5])):
            sx,sy,w,h=map(int,rect)
            if w and h:canvas.alpha_composite(images[ident].crop((sx,sy,sx+w,sy+h)),(int(x),int(y)))
        snapshots[name]=canvas
        if name.startswith('box-1') or name.startswith('longname-1'):
            gender=int(name.split('-')[3]) if name.startswith('box-1') else 1
            assert len(gender_icons)==(0 if gender==2 else 1)
            for x,y,icon in gender_icons:
                for gy in range(14):
                    for gx in range(14):
                        if icon.getpixel((gx,gy))[3]:
                            assert canvas.getpixel((x+gx,y+gy))==icon.getpixel((gx,gy)), 'Gender pixels covered by later layer'
                gender_checks+=1
        if name.startswith('fight-1'):
            # The complete name overlay must remain above every button texture.
            overlay_ids={i for n,i,t,b in text_boxes if n==name and t in ['電擊','十萬伏特','高速移動','電光一閃']}
            assert overlay_ids
            assert all(next(s[3] for s in sprites if s[0]==i)>max(s[3] for s in sprites if s[4][2]==192) for i in overlay_ids)
            for n,i,t,b in text_boxes:
                if n!=name:continue
                if t in ['電擊','十萬伏特','高速移動','電光一閃']:
                    slot=['電擊','十萬伏特','高速移動','電光一閃'].index(t)
                    x=4+(slot%2)*188+14;y=6+(slot//2)*42+8
                    assert x<=b[0] and b[2]<=x+164 and y<=b[1] and b[3]<=y+30,(name,t,b)
                elif t=='PP' or re.fullmatch(r'\d+/\d+',t):
                    assert 402<=b[0] and b[2]<=494 and 46<=b[1] and b[3]<=78,(name,t,b)
    assert all(label in all_text for label in ['戰鬥','背包','寶可夢','逃跑'])
    assert len([t for t in all_text if t=='電'])>0
    for name,ident,text,box in text_boxes:
        if not (name.startswith('box-1') or name.startswith('longname-1')):continue
        base=16 if name.split('-')[2]=='1' else 34
        assert text not in ('♂','♀'), 'Chinese gender still depends on font metrics'
        assert box[0]>=base+8 and box[2]<=base+112 and box[3]<=34,(name,text,box)
    assert all(images[i].tobytes()==originals[path].tobytes() for i,path in loaded.items()), 'Shared original texture mutated'
    assert all(snapshots[name].tobytes()==snapshots['original-'+name].tobytes() for name,_ in english_specs), 'English scene regression'
    OUT.mkdir(parents=True,exist_ok=True)
    for name,rect in [('command-1-0-0',(248,288,512,384)),('fight-1-1-14',(0,288,512,384)),('fight-1-1-30',(0,288,512,384)),
                      ('box-1-1-1-2',(0,0,260,62)),('box-1-1-0-2',(0,0,260,62)),('box-1-0-0-100',(0,0,260,84))]:
        im=snapshots[name].crop(rect).convert('RGB');save_preview(im,OUT/f'{name}-1x.png')
        save_preview(im.resize((im.width*3,im.height*3),Image.Resampling.NEAREST),OUT/f'{name}-3x.png')
    assert all(f.digest(Path(p).read_bytes())==h for p,h in source_hashes.items())
    report={'passed':True,'scenes_checked':len(frames),'text_calls_checked':len(text_boxes),'cache_isolation':True,
            'failed_copy_cleanup_checked':True,'font_restoration_after_error_checked':True,
            'gender_icons_unoccluded':gender_checks,'pp_actual_inner_bounds':[402,494],
            'english_scenes_byte_identical':len(english_specs),'shared_original_textures_unchanged':True,
            'source_images_unchanged':True,'game_started':False,'scripts_sha256':f.digest(archive.read_bytes()),
            'language_sha256':f.digest((f.ARTIFACTS/'release/fire-ash-zh-tw-preview/Data/traditional_chinese.dat').read_bytes()),
            'scope':'Actual battle classes with bitmap operations and z-order composed on CPU; not an in-game screenshot.'}
    f.json_write(REPORT,report);print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scripts',type=Path)
    parser.add_argument('--report',type=Path)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.report:REPORT=args.report
    if args.output:OUT=args.output
    try:main(args.scripts)
    except Exception as e:
        f.json_write(REPORT,{'passed':False,'error':str(e)})
        raise
