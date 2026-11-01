"""Find real Ruby lookup strings absent from the shipped messages table.

AST parsing never executes game scripts. Dynamic datasets are deliberately scoped
to the actual callers inspected in the runtime audit, not arbitrary Ruby strings.
"""
import json
import re
import zlib
from functools import lru_cache

import fire_ash as f
from ruby_vm import RubyVM

AST_WALKER = r'''
def fire_ash_catalog_walk(node, out)
  return unless node.is_a?(RubyVM::AbstractSyntaxTree::Node)
  if node.type == :FCALL
    method, args = node.children
    if [:_INTL, :_ISPRINTF, :pbMessage, :pbConfirmMessage, :pbConfirmMessageSerious].include?(method)
      arg = args && args.children[0]
      if arg.is_a?(RubyVM::AbstractSyntaxTree::Node) && arg.type == :STR
        text = arg.children[0]
        out << [node.first_lineno, method, Messages.stringToKey(text).unpack1('H*')].join("\t")
      end
    end
  elsif node.type == :STR
    text = node.children[0]
    out << [node.first_lineno, 'literal', Messages.stringToKey(text).unpack1('H*')].join("\t")
  end
  node.children.each { |child| fire_ash_catalog_walk(child, out) }
end
'ready'
'''


def entries(vm, source):
    vm.put('$fire_ash_catalog_source', source)
    packed = vm.evaluate('out=[]; fire_ash_catalog_walk(RubyVM::AbstractSyntaxTree.parse($fire_ash_catalog_source),out); out.join("\\n")')
    return [(int(line), kind, bytes.fromhex(value).decode())
            for line, kind, value in (row.split('\t') for row in packed.splitlines())]


def initialize(vm, scripts):
    method = re.search(r'  def self.stringToKey\(str\).*?\n  end', scripts['Intl_Messages'], re.S)[0]
    vm.evaluate('class Messages\n' + method + '\nend\n"ready"')
    vm.evaluate(AST_WALKER)
    probe = entries(vm, r'''_INTL('single'); _INTL("a\nb"); _INTL("a\\nb"); # _INTL("comment")''')
    assert [v for _, k, v in probe if k == '_INTL'] == ['single', 'a\nb', r'a\nb']


@lru_cache(maxsize=1)
def collect(game):
    scripts = {f.text(row[1]): zlib.decompress(row[2]).decode('utf-8')
               for row in f.loads((game / 'Data/Scripts.rxdata').read_bytes())}
    original_ui = set(f.loads(f.source_data(game)[24]._dump())[0])
    vm = RubyVM(f.GAME)
    initialize(vm, scripts)
    sources = {}
    for name, code in scripts.items():
        for line, kind, value in entries(vm, code):
            dynamic = (name in ('PWC Battle', 'Grandeur Club') and value.startswith(('\\b', '\\r')) or
                       name == 'UI_EnemyBuffs' and value.startswith('Enemy Pokémon') or
                       name == 'PokeBattle_Battle' and value.startswith('The battlefield '))
            if kind == 'literal' and not dynamic:
                continue
            if value in original_ui or not re.search('[A-Za-z]', value):
                continue
            sources.setdefault(value, {'section': 103, 'en': value, 'script': name, 'line': line})
    # These headers are composed before _INTL; all inputs are finite script constants.
    for challenge in ('', 'Practice', 'Club', 'Gauntlet', 'Mayhem', 'Sync', 'Titan', 'Duet', 'DESPAIR'):
        for difficulty in ('', ' - Practice', ' - Veteran', ' - Ace', ' - Master'):
            value = (challenge + ' Challenge Team' + difficulty).strip()
            if value not in original_ui:
                sources.setdefault(value, {'section': 103, 'en': value, 'script': 'UI_ShowChallengeTeam', 'line': 224})
    rows = list(sources.values())
    rows.append({'section': 104, 'en': "\\bHere's your team in case you need a screenshot for proof of your beating me.",
                 'maps': [141, 151, 214], 'reason': 'Show Text missing from shipped map tables'})
    # The extracted baseline contains only the core archive; pin the installed plugin source.
    packed = (f.GAME / 'Data/PluginScripts.rxdata').read_bytes()
    assert f.digest(packed) == '1b955ab8f42392f5b5b3a9a199285e208907a2faedd460dfd2519e5e8523eb6c', 'Plugin source changed'
    known = original_ui | set(sources)
    for plugin, metadata, files in f.loads(packed):
        for filename, compressed in files:
            name = f.text(plugin) + '/' + f.text(filename)
            code = zlib.decompress(compressed).decode('utf-8')
            for line, kind, value in entries(vm, code):
                lair_option = name.endswith('/Max Lair Controls.rb') and value in ('View Map','View Party','View Record','Leave Lair')
                if kind == 'literal' and not lair_option:
                    continue
                if value in known or not re.search('[A-Za-z]', value):
                    continue
                rows.append({'section': 103, 'en': value, 'script': name, 'line': line})
                known.add(value)
    return rows


if __name__ == '__main__':
    rows = collect(f.ARTIFACTS / 'data/fire-ash-work/original-baseline')
    # New source batches only; never silently rewrite a translated batch.
    for index, start in enumerate(range(0, len(rows), 80), 130):
        path = f.ROOT / f'translation-source/batches/{index}-runtime-missing.jsonl'
        payload = ''.join(json.dumps(row, ensure_ascii=False)+'\n' for row in rows[start:start+80])
        if path.exists() and path.read_text(encoding='utf-8') != payload:
            raise ValueError(f'Source batch changed: {path}')
        if not path.exists():
            path.write_text(payload, encoding='utf-8', newline='\n')
        print(path.name, len(rows[start:start+80]), f.digest(payload.encode()))
