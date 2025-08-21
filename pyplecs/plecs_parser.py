"""PLECS file parser utilities.

Provides functions to parse .plecs files and extract:
- Component blocks (Type, Name, Parameters)
- InitializationCommands (MATLAB-like variable assignments)

The parser is intentionally lightweight (regex + brace matching) and
works with the typical flattened .plecs files used in this repo.
"""
from pathlib import Path
import re
from typing import List, Dict, Any


def _find_matching_brace(text: str, start_idx: int) -> int:
    """Find index of matching closing brace '}' starting from start_idx which should point at '{'."""
    depth = 0
    for i in range(start_idx, len(text)):
        ch = text[i]
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return i
    raise ValueError("No matching closing brace found")


def _extract_component_blocks(text: str) -> List[str]:
    blocks = []
    for m in re.finditer(r'\bComponent\s*\{', text):
        start = m.start()
        open_brace = text.find('{', start)
        end = _find_matching_brace(text, open_brace)
        blocks.append(text[start:end+1])
    return blocks


def _parse_parameters(block_text: str) -> Dict[str, str]:
    params = {}
    # find Parameter { ... } blocks inside the component
    for m in re.finditer(r'\bParameter\s*\{', block_text):
        ob = block_text.find('{', m.start())
        cb = _find_matching_brace(block_text, ob)
        ptxt = block_text[ob+1:cb]
        # Variable "name" and Value "value" (often quoted)
        var_m = re.search(r'\bVariable\s+"([^"]+)"', ptxt)
        val_m = re.search(r'\bValue\s+"([^"]*)"', ptxt)
        if var_m:
            var = var_m.group(1).strip()
            if val_m:
                val = val_m.group(1).strip()
            else:
                # fallback: unquoted value
                vm = re.search(r'\bValue\s+([^\s\n\r}]+)', ptxt)
                val = vm.group(1).strip() if vm else ''
            params[var] = val
    return params


def _parse_component(block_text: str) -> Dict[str, Any]:
    # Type (unquoted token) and Name (quoted string)
    type_m = re.search(r'\bType\s+"?([^"\s]+)"?', block_text)
    name_m = re.search(r'\bName\s+"([^"]+)"', block_text)
    comp_type = type_m.group(1).strip() if type_m else None
    name = name_m.group(1).strip() if name_m else None
    params = _parse_parameters(block_text)
    return {'type': comp_type, 'name': name, 'parameters': params}


def _extract_init_commands(text: str) -> str:
    # Locate InitializationCommands and collect all adjacent quoted strings
    m = re.search(r'\bInitializationCommands\b', text)
    if not m:
        return ''
    start = m.end()
    # search forward until InitialState or next top-level token
    end_marker = text.find('\n  InitialState', start)
    if end_marker == -1:
        # fallback: 10000 chars ahead
        snippet = text[start:start+10000]
    else:
        snippet = text[start:end_marker]
    # collect all quoted literals in the snippet and concatenate
    parts = re.findall(r'"([^"]*)"', snippet, flags=re.S)
    joined = ''.join(parts)
    if not joined:
        return ''
    # decode common escaped sequences (\n, \t) that appear in quoted fragments
    try:
        s = joined.encode('utf-8').decode('unicode_escape')
    except Exception:
        s = joined
    # normalize newlines and whitespace
    s = re.sub(r"\r\n|\r", "\n", s)
    # collapse repeated whitespace
    s = re.sub(r"[\t ]+", " ", s)
    # fix common split exponent patterns where tokens were broken across quoted strings
    # examples: '100e' '\n' '3'  -> '100e3'
    s = re.sub(r'(?i)(\d+)\s*[eE]\s*[\n\s]*([+-]?\d+)', r'\1e\2', s)
    # also fix patterns like '1e -6' -> '1e-6'
    s = re.sub(r'(?i)(\d+\.?\d*)\s*[eE]\s*([+-])\s*(\d+)', r'\1e\2\3', s)
    return s


def _parse_init_vars(init_text: str) -> Dict[str, Any]:
    # remove MATLAB '%%' comment lines and inline '%' comments
    lines = []
    for ln in init_text.splitlines():
        if ln.strip().startswith('%%'):
            continue
        ln = re.sub(r'%.*', '', ln)
        lines.append(ln)
    txt = '\n'.join(lines)
    # normalize whitespace
    txt = txt.replace('\r', '\n')

    # split into statements by semicolon or newline; keep order
    stmts = [s.strip() for s in re.split(r';|\n', txt) if s.strip()]
    result: Dict[str, Any] = {}
    for s in stmts:
        m = re.match(r'^([A-Za-z_]\w*)\s*=\s*(.+)$', s)
        if not m:
            continue
        name = m.group(1)
        expr = m.group(2).strip()
        # try parse numeric literal
        if re.fullmatch(r'[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?', expr):
            try:
                if '.' in expr or 'e' in expr or 'E' in expr:
                    result[name] = float(expr)
                else:
                    result[name] = int(expr)
                continue
            except Exception:
                pass
        # fallback: keep expression as string
        result[name] = expr
    return result


def parse_plecs_file(path: str) -> Dict[str, Any]:
    """Parse a .plecs file and return a dict with components and init vars."""
    p = Path(path)
    text = p.read_text(encoding='utf-8')
    components = []
    for block in _extract_component_blocks(text):
        components.append(_parse_component(block))
    init_cmds = _extract_init_commands(text)
    init_vars = _parse_init_vars(init_cmds) if init_cmds else {}
    return {'file': str(p), 'components': components, 'init_vars': init_vars}


def plecs_overview(path: str) -> Dict[str, Any]:
        """Return a compact dict overview for a .plecs file suitable for orchestration.

        Structure:
            {
                'file': str,
                'components': {name_or_index: {type, name, parameters}},
                'init_vars': {..}
            }
        """
        parsed = parse_plecs_file(path)
        comps = {}
        for i, c in enumerate(parsed['components']):
                key = c.get('name') or f"component_{i}"
                # if duplicate names, append index
                if key in comps:
                        key = f"{key}_{i}"
                comps[key] = {'type': c.get('type'), 'name': c.get('name'), 'parameters': c.get('parameters')}
        return {'file': parsed['file'], 'components': comps, 'init_vars': parsed['init_vars']}


def scan_plecs_dir(dirpath: str) -> Dict[str, Dict[str, Any]]:
    """Scan directory for .plecs files and parse each one.

    Returns a mapping filename -> parse result.
    """
    res = {}
    base = Path(dirpath)
    for p in sorted(base.glob('**/*.plecs')):
        try:
            res[str(p)] = parse_plecs_file(str(p))
        except Exception as e:
            res[str(p)] = {'error': str(e)}
    return res
