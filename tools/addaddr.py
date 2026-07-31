#!/usr/bin/env python3
"""
addaddr.py — Annotate source/zanac.asm with per-line ROM addresses.

Writes source/zanac-new.asm where every instruction and DB/DW line gets
a ; 0xXXXX tag prepended to its comment (or appended if there is none).

Usage:
  .venv/bin/python tools/addaddr.py
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASM = ROOT / "source" / "zanac.asm"
OUT = ROOT / "source" / "zanac-new.asm"
LST = ROOT / "build" / "zanac-addr.lst"

COMM_COL = 68  # column where comments start (matches redisasm.py)
ROM_BASE = 0x4000

# ── 1. Assemble to get per-line addresses ─────────────────────────────────────

print("Running sjasmplus to generate listing …")
LST.parent.mkdir(parents=True, exist_ok=True)
r = subprocess.run(
    ["sjasmplus", f"--lst={LST}", "--raw=/dev/null", str(ASM)],
    capture_output=True,
    text=True,
)
# JR-range errors are non-fatal for address tracking; anything else is fatal.
fatal = [
    ln
    for ln in r.stderr.splitlines()
    if "error:" in ln and "out of range" not in ln and "Target" not in ln
]
if fatal:
    print("\n".join(fatal), file=sys.stderr)
    sys.exit(1)

# ── 2. Parse listing → {1-based line number: address} ─────────────────────────

# Listing line format (sjasmplus 1.21):
#   "  NNN  AAAA [BB BB BB ...]   source_text"
_LST_RE = re.compile(r"^\s*(\d+)\s+([0-9A-Fa-f]{4})\s")

line_addrs: dict[int, int] = {}
for lst_line in LST.read_text(encoding="utf-8").splitlines():
    m = _LST_RE.match(lst_line)
    if m:
        lnum = int(m.group(1))
        addr = int(m.group(2), 16)
        if addr >= ROM_BASE and (lnum not in line_addrs):
            line_addrs[lnum] = addr

print(f"  {len(line_addrs)} lines with ROM addresses found in listing.")

# ── 3. Annotate source file ───────────────────────────────────────────────────

_PURE_COMMENT_RE = re.compile(r"^\s*;")
_DIRECTIVE_SKIP = re.compile(r"^\s+(ORG|EQU|MACRO|ENDM|IF|ENDIF|END)\b", re.IGNORECASE)

src_lines = ASM.read_text(encoding="utf-8").splitlines(keepends=True)
out_lines: list[str] = []
annotated = 0

for i, raw in enumerate(src_lines, 1):
    line = raw.rstrip("\n")
    addr = line_addrs.get(i)

    # Only touch indented lines with a real ROM address
    if (
        addr is None
        or not line
        or not line[0].isspace()  # blank or label
        or _PURE_COMMENT_RE.match(line)  # pure comment
        or _DIRECTIVE_SKIP.match(line)  # assembler directives
    ):
        out_lines.append(raw)
        continue

    tag = f"0x{addr:04x}"
    semi = line.find(";")

    if semi >= 0:
        before = line[:semi]
        rest = line[semi + 1 :].lstrip()
        if rest:
            new_line = f"{before}; {tag}  {rest}"
        else:
            new_line = f"{before}; {tag}"
    else:
        padded = f"{line:<{COMM_COL}}"
        new_line = f"{padded} ; {tag}"

    out_lines.append(new_line + "\n")
    annotated += 1

OUT.write_text("".join(out_lines), encoding="utf-8")
print(f"  {annotated} lines annotated → {OUT.relative_to(ROOT)}")

# ── 4. Quick sanity check ─────────────────────────────────────────────────────

# Count lines where we can spot the address in the new file vs old file
new_text = OUT.read_text(encoding="utf-8")
addr_pat = re.compile(r"; 0x[0-9A-Fa-f]{4}\b")
tagged = sum(1 for ln in new_text.splitlines() if addr_pat.search(ln))
print(f"  {tagged} lines carry a ; 0xXXXX tag in the output.")
print("Done.")
