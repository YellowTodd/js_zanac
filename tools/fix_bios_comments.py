#!/usr/bin/env python3
"""Fix wrong BIOS `-> NAME` arrow comments in source/zanac.asm.

The Ghidra disassembler used a misaligned BIOS symbol table, so its arrow
comments on CALL/JP/JR to BIOS addresses (0x0000-0x01FF) are systematically
wrong. This rewrites each arrow to the correct name from kb/symbols/0x0000-bios/
(and 0x0000-vectors/). Comments only — ROM bytes are untouched.

Usage:
  python tools/fix_bios_comments.py            # dry run (report)
  python tools/fix_bios_comments.py --apply    # rewrite in place
"""
import re, glob, sys

ASM = "source/zanac.asm"

def bios_map():
    m = {}
    for p in glob.glob('kb/symbols/0x0000-bios/*.md') + glob.glob('kb/symbols/0x0000-vectors/*.md'):
        t = open(p).read()
        a = re.search(r'^address:\s*(0x[0-9a-fA-F]+)', t, re.M)
        n = re.search(r'^name:\s*(\S+)', t, re.M)
        if a and n:
            name = n.group(1)
            if name.startswith('bios_'):
                name = name[5:]
            m[int(a.group(1), 16)] = name.upper()
    return m

BRANCH = re.compile(r'^\s*(CALL|JP|JR)\b', re.I)  # BIOS reached via CALL/JP only (RST 0x20 is self-annotated)
HEX = re.compile(r'0x([0-9a-fA-F]+)')
ARROW = re.compile(r'(->\s*)(\S+)')

def main():
    apply = '--apply' in sys.argv
    m = bios_map()
    lines = open(ASM).read().split('\n')
    changes = []
    no_arrow = []
    for i, ln in enumerate(lines):
        if ';' not in ln:
            continue
        code, comment = ln.split(';', 1)
        if not BRANCH.match(code):
            continue
        hexes = HEX.findall(code)
        if not hexes:
            continue
        target = int(hexes[-1], 16)        # branch target operand
        if target not in m:
            continue
        correct = m[target]
        am = ARROW.search(comment)
        if am:
            cur = am.group(2)
            if cur != correct:
                newcomment = comment[:am.start()] + '-> ' + correct + comment[am.end():]
                lines[i] = code + ';' + newcomment
                changes.append((i + 1, target, cur, correct))
        else:
            no_arrow.append((i + 1, target, correct, ln.rstrip()))
    print(f"{len(changes)} arrows to fix; {len(no_arrow)} BIOS-branch lines without an arrow")
    from collections import Counter
    c = Counter((t, cur, cor) for _, t, cur, cor in changes)
    for (t, cur, cor), n in sorted(c.items()):
        print(f"  0x{t:04X}: {cur:16} -> {cor:10}  ({n}x)")
    if no_arrow:
        print("\nBIOS-branch lines WITHOUT an arrow (left untouched):")
        for ln_no, t, cor, raw in no_arrow:
            print(f"  L{ln_no}: 0x{t:04X} ({cor})  {raw.strip()}")
    if apply:
        open(ASM, 'w').write('\n'.join(lines))
        print("\nAPPLIED.")
    else:
        print("\n(dry run — pass --apply to write)")

if __name__ == '__main__':
    main()
