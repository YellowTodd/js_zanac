#!/usr/bin/env python3
"""Naming-consistency inventory: KB `name:` fields vs source/zanac.asm labels.

Pass 1 of sprint 0068.  Joins every KB symbol/data entry against the labels
present in the disassembly and classifies each entry:

  (a) unlabeled  — KB-named entry whose asm label is still generic
                   (SUB_ram_/LAB_ram_) or missing entirely.
  (b) misnomer   — asm carries a *named* label that differs from the KB name,
                   or the KB entry's own body flags its name as a legacy
                   misnomer ("legacy misnomer" / "read it as" / "Correction").
  (c) local      — generic asm labels with no KB entry at their address; these
                   are JR/DJNZ branch targets and are *excluded* from renaming.

Also reports entries whose inbound `-> {SUB,LAB}_ram_ADDR` arrow comments are
still generic (the align target for tools/rename_symbol.py --from-kb).

Exit status is 1 while any (a) or (b) item is unresolved, so it doubles as the
sprint's completion gate.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASM = ROOT / "source" / "zanac.asm"
sys.path.insert(0, str(ROOT / "tools"))

from zanackb.parser import load_kb  # noqa: E402

LABEL_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):(?:\s|$)")
ADDR_COMMENT_RE = re.compile(r";\s*0x([0-9A-Fa-f]{4})\b")
GENERIC_RE = re.compile(r"^(SUB_ram|LAB_ram)_[0-9A-Fa-f]+$")
ARROW_GENERIC_RE = re.compile(r"->\s*(?:SUB_ram|LAB_ram)_([0-9A-Fa-f]{4})\b")
# Phrases a KB body uses to flag its *current* name as wrong (not mere history
# like "was labelled ...", which describes a superseded pre-KB Ghidra label).
MISNOMER_RE = re.compile(r"legacy misnomer|read it as", re.IGNORECASE)

ROM_LO, ROM_HI = 0x4000, 0xBFFF


def parse_asm(lines: list[str]):
    """Return (addr->label, generic_addrs, arrow_addrs)."""
    addr_label: dict[int, str] = {}
    pending_labels: list[str] = []
    for ln in lines:
        m = LABEL_RE.match(ln)
        if m:
            pending_labels.append(m.group(1))
            continue
        if ln.lstrip().startswith(";"):
            continue  # comment-only line (e.g. memory-map banner) — not content
        am = ADDR_COMMENT_RE.search(ln)
        if am and pending_labels:
            addr = int(am.group(1), 16)
            # a content line resolves the labels stacked immediately above it
            for lab in pending_labels:
                addr_label.setdefault(addr, lab)
            pending_labels = []
        elif am:
            pending_labels = []
    arrow_addrs: dict[int, int] = {}
    for ln in lines:
        for m in ARROW_GENERIC_RE.finditer(ln):
            a = int(m.group(1), 16)
            arrow_addrs[a] = arrow_addrs.get(a, 0) + 1
    return addr_label, arrow_addrs


def main() -> None:
    kb = load_kb(ROOT / "kb")
    lines = ASM.read_text().splitlines()
    addr_label, arrow_addrs = parse_asm(lines)
    kb_addrs = {e.address for e in kb.entries}

    unlabeled = []   # (a)
    misnomer = []    # (b)
    stale_arrows = []  # residual generic arrow comments

    for e in sorted((x for x in kb.entries if ROM_LO <= x.address <= ROM_HI),
                    key=lambda x: x.address):
        lab = addr_label.get(e.address)
        if lab is None:
            unlabeled.append((e, "MISSING"))
        elif GENERIC_RE.match(lab):
            unlabeled.append((e, lab))
        elif lab != e.name:
            misnomer.append((e, lab, "asm-label-differs"))
        # KB body self-flags name as a misnomer
        if MISNOMER_RE.search(e.body) and (lab is None or lab == e.name):
            misnomer.append((e, lab or "MISSING", "kb-flagged"))
        # residual generic inbound arrows
        if e.address in arrow_addrs:
            stale_arrows.append((e, arrow_addrs[e.address]))

    # (c) generic asm labels with no KB entry = local branch targets
    local = sorted(a for a, lab in addr_label.items()
                   if GENERIC_RE.match(lab) and a not in kb_addrs)

    print(f"# Naming audit — {ASM.relative_to(ROOT)} vs KB\n")

    print(f"## (a) Unlabeled KB entries — {len(unlabeled)}\n")
    for e, cur in unlabeled:
        print(f"  0x{e.address:04X}  {e.name:36s} [{e.kind}]  asm={cur}")

    print(f"\n## (b) Misnomers — {len(misnomer)}\n")
    for e, cur, why in misnomer:
        print(f"  0x{e.address:04X}  KB={e.name:32s} asm={cur:24s} ({why})")

    print(f"\n## (c) Local labels (generic, no KB entry — excluded) — {len(local)}\n")
    print("   " + ", ".join(f"0x{a:04X}" for a in local[:40])
          + (" ..." if len(local) > 40 else ""))

    print(f"\n## Residual generic arrow comments (align target) — {len(stale_arrows)} entries\n")
    tot = sum(n for _, n in stale_arrows)
    print(f"   {tot} arrow lines across {len(stale_arrows)} documented addresses")

    clean = not unlabeled and not misnomer
    print(f"\n=> {'CLEAN — 0 (a)/(b) items' if clean else 'WORK REMAINS'}")
    sys.exit(0 if clean else 1)


if __name__ == "__main__":
    main()
