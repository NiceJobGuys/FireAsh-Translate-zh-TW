"""Three-way script-block merge for a reviewed UI update; never installs files."""
import argparse
import json
import zlib
from pathlib import Path
import fire_ash as f
from ruby_vm import RubyVM


def merge(base, candidate, current):
    if not (len(base)==len(candidate)==len(current)):
        raise ValueError('Script count differs; manual compatibility review required')
    output=[]; changed=[]
    for old,new,live in zip(base,candidate,current):
        if not (old[:2]==new[:2]==live[:2]):
            raise ValueError('Script order/identity differs; refusing automatic merge')
        name=f.text(old[1])
        if old==new:
            output.append(live)
        elif live==old or live==new:
            output.append(new)
            if live!=new:changed.append(name)
        else:
            raise ValueError(f'Both updates change {name}; refusing to overwrite')
    return output,changed


def main(args):
    # A conflicting independent modification must never be silently discarded.
    assert merge([[1,'a',b'old'],[2,'b',b'old']],[[1,'a',b'new'],[2,'b',b'old']],
                 [[1,'a',b'old'],[2,'b',b'other']])[0]==[[1,'a',b'new'],[2,'b',b'other']]
    try:merge([[1,'a',b'old']],[[1,'a',b'new']],[[1,'a',b'other']])
    except ValueError:pass
    else:raise AssertionError('Conflict accepted')
    blobs=[p.read_bytes() for p in (args.base,args.candidate,args.current)]
    assert f.digest(blobs[0])==args.expect_base,'Base changed'
    assert f.digest(blobs[2])==args.expect_current,'Installed scripts changed'
    base,candidate,current=map(f.loads,blobs)
    output,changed=merge(base,candidate,current)
    assert changed and set(changed)<={'PokeBattle_SceneElements','PokeBattle_SceneMenus','FireAsh_ZHTW_Runtime','FireAsh_ZHTW_Font'},changed
    result=f.writes(output)
    restored=f.loads(result)
    assert restored==output
    assert all(a==b for a,b in zip(current,restored) if f.text(a[1]) not in changed)
    destination=args.package.resolve()
    assert destination.is_relative_to(f.ARTIFACTS.resolve()) and destination!=f.ARTIFACTS.resolve()
    destination.mkdir(parents=True,exist_ok=False)
    (destination/'translation-base.rxdata').write_bytes(blobs[1])
    (destination/'Scripts.rxdata').write_bytes(result)
    vm=RubyVM(f.GAME)
    for row in restored:
        vm.put('$source',zlib.decompress(row[2]).decode('utf-8'))
        vm.evaluate('RubyVM::InstructionSequence.compile($source); "ok"')
    vm.put('$before',args.current.resolve().as_posix());vm.put('$after',(destination/'Scripts.rxdata').as_posix())
    native=vm.evaluate('a=Marshal.load(File.binread($before)); b=Marshal.load(File.binread($after)); '+
                      'raise "count changed" unless a.length==b.length; a.each_index.select { |i| a[i]!=b[i] }.map { |i| a[i][1] }.join("|")')
    assert set(native.split('|'))==set(changed)
    manifest={'version':'battle-ui-compatible','game':str(f.GAME),'relative':'Data/Scripts.rxdata',
              'original_sha256':f.digest(blobs[2]),'patched_sha256':f.digest(result),
              'base_sha256':f.digest(blobs[0]),'candidate_sha256':f.digest(blobs[1]),
              'changed_scripts':changed,'preserved_scripts':len(current)-len(changed),
              'validation':f'PASS: native Marshal and {len(restored)} script compilations; non-UI blocks byte-identical',
              'game_started':False}
    f.json_write(destination/'manifest.json',manifest)
    print(json.dumps(manifest,ensure_ascii=False,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('base','candidate','current','package'):p.add_argument('--'+name,type=Path,required=True)
    for name in ('expect-base','expect-current'):p.add_argument('--'+name,required=True)
    main(p.parse_args())
