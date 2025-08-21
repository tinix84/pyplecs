import sys
sys.path.insert(0, 'D:/git/pyplecs')
from pyplecs.plecs_parser import plecs_overview
import json

ov = plecs_overview('data/simple_buck.plecs')
print(json.dumps(ov, indent=2, ensure_ascii=False))
