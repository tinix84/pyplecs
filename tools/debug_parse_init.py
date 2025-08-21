import sys
sys.path.insert(0, 'D:/git/pyplecs')
from pyplecs.plecs_parser import _extract_init_commands
s = _extract_init_commands(open('data/simple_buck.plecs','r',encoding='utf-8').read())
print('RAW INIT_TEXT:\n', s)
# mimic parsing
import re
lines = []
for ln in s.splitlines():
    if ln.strip().startswith('%%'):
        continue
    ln2 = re.sub(r'%.*', '', ln)
    lines.append(ln2)
txt = '\n'.join(lines)
print('\nCLEANED TEXT:\n', txt)
stmts = [st.strip() for st in re.split(r';|\n', txt) if st.strip()]
print('\nSTATEMENTS:')
for i,st in enumerate(stmts):
    print(i, repr(st))

import re
for st in stmts:
    m = re.match(r'^([A-Za-z_]\w*)\s*=\s*(.+)$', st)
    print('MATCH', st, '->', bool(m))
    if m:
        print('  name=', m.group(1), 'expr=', m.group(2))
