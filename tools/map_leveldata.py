#!/usr/bin/env python3
"""Map all code references into the 0x9B64-0xBE27 level-data block.

Scans source/zanac.asm for LD rr,imm16 / CALL / JP / JR targets that land
inside the block, plus 16-bit LE pointers embedded in DB lines that point into
the block. Prints, per referenced address, who references it and how.
"""
import re, sys
from collections import defaultdict

LO, HI = 0x9B64, 0xBE27
SRC = "source/zanac.asm"

# addr comment at end of each line: ; 0xNNNN
addr_re = re.compile(r";\s*0x([0-9a-fA-F]{4})")
imm_re  = re.compile(r"\b(LD|CALL|JP|JR)\b.*?0x([0-9a-fA-F]{3,4})")
db_re   = re.compile(r"\bDB\b\s+(.*?)\s*;")

def line_addr(line):
    m = addr_re.search(line)
    return int(m.group(1), 16) if m else None

code_refs = defaultdict(list)   # target -> list of (src_addr, mnemonic-context)
db_ptrs   = defaultdict(list)   # target -> list of db_addr where LE ptr found

lines = open(SRC).read().splitlines()
for ln in lines:
    src_addr = line_addr(ln)
    # code immediate refs
    if "DB" not in ln:
        m = imm_re.search(ln)
        if m:
            tgt = int(m.group(2), 16)
            if LO <= tgt <= HI:
                ctx = ln.split(";")[0].strip()
                code_refs[tgt].append((src_addr, ctx))
    else:
        m = db_re.search(ln)
        if m and src_addr is not None:
            byts = [int(b, 16) for b in re.findall(r"0x([0-9a-fA-F]{2})", m.group(1))]
            for i in range(len(byts) - 1):
                ptr = byts[i] | (byts[i+1] << 8)
                if LO <= ptr <= HI:
                    db_ptrs[ptr].append(src_addr + i)

print(f"=== CODE references into [{LO:#06x},{HI:#06x}] ===")
for tgt in sorted(code_refs):
    print(f"{tgt:#06x}:")
    for src, ctx in code_refs[tgt]:
        s = f"{src:#06x}" if src else "?"
        print(f"    from {s}: {ctx}")

print(f"\n=== distinct DB-embedded LE pointers into block (count) ===")
# summarize by high byte cluster
buckets = defaultdict(int)
for tgt in db_ptrs:
    buckets[tgt & 0xFF00] += len(db_ptrs[tgt])
for hi in sorted(buckets):
    print(f"  0x{hi:04X}xx region: {buckets[hi]} pointer occurrences")
print(f"  total distinct targets: {len(db_ptrs)}")
