"""Map DB blocks in zanac.asm and cross-reference KB-referenced addresses.

Usage:
    .venv/bin/python tools/map_db_sections.py [--rom-only] [--asm source/zanac.asm]

Output:
    1. All contiguous DB blocks with exact byte ranges (ROM space 0x4000–0xBFFF only).
    2. KB-referenced addresses that fall inside those blocks (these are decode candidates).

The block end is computed from actual DB byte counts, not a heuristic, so results
are exact — no false positives from boundary overestimation.

A KB address is flagged as "code" when referenced via calls: or called_by:,
"data" when referenced in body text only, and "unknown" when unclear.
"""

import re
import sys
from pathlib import Path

ASM_PATH   = Path("source/zanac.asm")
KB_ROOT    = Path("kb")
ROM_START  = 0x4000
ROM_END    = 0xC000  # exclusive


# ── 1. Parse DB blocks from the ASM ──────────────────────────────────────────

def parse_db_blocks(asm_path: Path) -> list[tuple[int, int, int, int]]:
    """Return list of (start_addr, end_addr_exclusive, first_line, last_line).

    Contiguous DB lines are grouped into one block. End is computed from
    the ACTUAL byte count of each row (not last_row + 16).
    """
    DB_RE  = re.compile(r'^\s+DB\s+(.*?)\s*(?:;.*)?$', re.IGNORECASE)
    ADDR_RE = re.compile(r';\s*(0x[0-9a-fA-F]+)\s*$')

    blocks: list[tuple[int, int, int, int]] = []
    cur_start = cur_end = cur_first = None
    prev_end = None

    with asm_path.open() as f:
        for lineno, line in enumerate(f, 1):
            m = DB_RE.match(line)
            addr_m = ADDR_RE.search(line)
            if m and addr_m:
                addr = int(addr_m.group(1), 16)
                if ROM_START <= addr < ROM_END:
                    # Count bytes in this row
                    operands = m.group(1).split(';')[0]  # strip inline comment
                    byte_count = len([x for x in operands.split(',') if x.strip()])
                    row_end = addr + byte_count

                    if cur_start is None or addr != prev_end:
                        # Start new block
                        if cur_start is not None:
                            blocks.append((cur_start, cur_end, cur_first, lineno - 1))
                        cur_start = addr
                        cur_first = lineno
                    cur_end = row_end
                    prev_end = row_end
                    continue

            if cur_start is not None:
                blocks.append((cur_start, cur_end, cur_first, lineno - 1))
                cur_start = cur_end = cur_first = prev_end = None

    if cur_start is not None:
        blocks.append((cur_start, cur_end, cur_first, -1))

    return blocks


# ── 2. Collect KB-referenced addresses ───────────────────────────────────────

def collect_kb_addresses(kb_root: Path) -> dict[int, list[dict]]:
    """Return {addr: [{file, kind}]} where kind is 'calls', 'called_by', or 'body'."""
    HEX4 = re.compile(r'0x([0-9a-fA-F]{4})\b')
    result: dict[int, list[dict]] = {}

    for md in sorted(kb_root.rglob("*.md")):
        try:
            text = md.read_text()
        except Exception:
            continue

        # Split frontmatter from body
        parts = text.split('---', 2)
        frontmatter = parts[1] if len(parts) >= 3 else ''
        body        = parts[2] if len(parts) >= 3 else text

        # Parse calls: / called_by: lists
        for field in ('calls', 'called_by'):
            fm_re = re.compile(rf'^{field}:\s*\[([^\]]*)\]', re.MULTILINE)
            m = fm_re.search(frontmatter)
            if m:
                for tok in m.group(1).split(','):
                    tok = tok.strip()
                    hm = re.match(r'(0x[0-9a-fA-F]{4})', tok)
                    if hm:
                        addr = int(hm.group(1), 16)
                        result.setdefault(addr, []).append({'file': str(md), 'kind': field})

        # Body text: any 0xNNNN pattern (weaker signal)
        for hm in HEX4.finditer(body):
            addr = int(hm.group(1), 16)
            if ROM_START <= addr < ROM_END:
                if not any(e['file'] == str(md) and e['kind'] == 'body'
                           for e in result.get(addr, [])):
                    result.setdefault(addr, []).append({'file': str(md), 'kind': 'body'})

    return result


# ── 3. Cross-reference ────────────────────────────────────────────────────────

def cross_reference(
    blocks: list[tuple[int, int, int, int]],
    kb_addresses: dict[int, list[dict]],
) -> list[dict]:
    """Return list of {addr, block, refs} for addresses inside DB blocks."""
    hits = []
    for addr, refs in sorted(kb_addresses.items()):
        for (bstart, bend, bline1, bline2) in blocks:
            if bstart <= addr < bend:
                # Determine strongest reference kind
                kinds = {r['kind'] for r in refs}
                if 'calls' in kinds or 'called_by' in kinds:
                    classification = 'code'
                else:
                    classification = 'data?'

                # Deduplicate files
                files = sorted({r['file'] for r in refs})
                hits.append({
                    'addr': addr,
                    'block': (bstart, bend, bline1, bline2),
                    'refs': refs,
                    'files': files,
                    'classification': classification,
                })
                break
    return hits


# ── 4. Report ─────────────────────────────────────────────────────────────────

def report(blocks, hits):
    print(f"DB blocks in ROM space (0x{ROM_START:04X}–0x{ROM_END:04X}):")
    print(f"  {len(blocks)} blocks found\n")

    if not hits:
        print("No KB-referenced addresses fall inside any DB block.")
        return

    print(f"KB addresses inside DB blocks ({len(hits)} found):")
    print("=" * 72)

    code_hits  = [h for h in hits if h['classification'] == 'code']
    data_hits  = [h for h in hits if h['classification'] == 'data?']

    if code_hits:
        print(f"\n[CODE — called or jumped to] {len(code_hits)} address(es):\n")
        for h in code_hits:
            b = h['block']
            print(f"  0x{h['addr']:04X}  in DB block 0x{b[0]:04X}–0x{b[1]-1:04X}"
                  f"  (ASM lines {b[2]}–{b[3]})")
            call_files = sorted({r['file'] for r in h['refs']
                                 if r['kind'] in ('calls', 'called_by')})
            for f in call_files:
                kinds = [r['kind'] for r in h['refs'] if r['file'] == f]
                print(f"    ← {Path(f).name}  [{', '.join(sorted(set(kinds)))}]")

    if data_hits:
        print(f"\n[DATA? — body mention only] {len(data_hits)} address(es):\n")
        for h in data_hits:
            b = h['block']
            print(f"  0x{h['addr']:04X}  in DB block 0x{b[0]:04X}–0x{b[1]-1:04X}"
                  f"  (ASM lines {b[2]}–{b[3]})")
            for f in h['files']:
                print(f"    ← {Path(f).name}")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    asm_path = ASM_PATH
    for i, arg in enumerate(sys.argv[1:]):
        if arg == '--asm' and i + 1 < len(sys.argv) - 1:
            asm_path = Path(sys.argv[i + 2])

    blocks = parse_db_blocks(asm_path)
    kb_addresses = collect_kb_addresses(KB_ROOT)
    hits = cross_reference(blocks, kb_addresses)
    report(blocks, hits)


if __name__ == '__main__':
    main()
