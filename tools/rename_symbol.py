#!/usr/bin/env python3
"""Byte-neutral symbol renaming for source/zanac.asm  (sprint 0068).

`zanac.asm` uses **absolute hex operands** for every branch/call, so labels are
purely cosmetic: renaming a label or an arrow comment never changes an emitted
byte.  This tool exploits that to align the disassembly's labels with the KB's
canonical names.

Two forms:

  rename_symbol.py <old> <new>
      Rename a single label.  <old> may be a generic `SUB_ram_XXXX`/`LAB_ram_XXXX`
      label or an existing name.  Renames the `old:` definition line and every
      `-> old` (and `-> {SUB,LAB}_ram_ADDR` for old's address) arrow comment.
      Refuses if <new> already labels a different address, or <old> is
      absent/ambiguous.

  rename_symbol.py --from-kb [--start 0xLO] [--end 0xHI] [--apply]
      Batch pass: for every KB entry whose address is in [start, end] (default
      the 0x4000-0xBFFF ROM), make the asm label at that address equal the KB
      `name:` — renaming a generic/mismatched label, or inserting one if the
      entry has no label yet — and rewrite every inbound `-> {SUB,LAB}_ram_ADDR`
      arrow comment to the KB name.  Default is a dry-run report; pass --apply
      to write.

Every emitted byte is unchanged; run `tools/redisasm.py verify` after --apply.
"""
from __future__ import annotations

import argparse
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

ROM_LO, ROM_HI = 0x4000, 0xBFFF


# ---------------------------------------------------------------------------
# ASM model
# ---------------------------------------------------------------------------


def read_lines() -> list[str]:
    return ASM.read_text().splitlines()


def content_line_addr(line: str) -> int | None:
    """Address of a real instruction/data line (from its trailing `; 0xADDR`).

    Excludes label lines and comment-only lines (e.g. the memory-map banner
    `;   0x4000-0x7fff ...`), which would otherwise pollute the address index.
    """
    if LABEL_RE.match(line) or line.lstrip().startswith(";"):
        return None
    m = ADDR_COMMENT_RE.search(line)
    return int(m.group(1), 16) if m else None


def build_addr_index(lines: list[str]) -> dict[int, int]:
    """addr -> index of the first content line carrying that address comment."""
    idx: dict[int, int] = {}
    for i, ln in enumerate(lines):
        a = content_line_addr(ln)
        if a is not None:
            idx.setdefault(a, i)
    return idx


def label_defs(lines: list[str]) -> dict[str, int]:
    """label name -> line index of its `name:` definition."""
    out: dict[str, int] = {}
    for i, ln in enumerate(lines):
        m = LABEL_RE.match(ln)
        if m:
            out[m.group(1)] = i
    return out


def preceding_label_idx(lines: list[str], content_idx: int) -> int | None:
    """If the line immediately before *content_idx* is a label def, its index."""
    j = content_idx - 1
    if j >= 0 and LABEL_RE.match(lines[j]):
        return j
    return None


# ---------------------------------------------------------------------------
# Token retargeting (byte-neutral)
# ---------------------------------------------------------------------------
#
# A label token may appear three ways on a line:
#   1. as the definition        `LAB_ram_412a:`
#   2. as a symbolic operand     `JR NZ, LAB_ram_412a`   (relative JR/DJNZ)
#   3. in an arrow comment       `; 0x4120  -> LAB_ram_412a`
# Cases 1 and 3 never shift byte output or alignment (line-final / label-only).
# Case 2 changes the operand width, so the tab-padded comment must be re-aligned
# to its original column (comments sit at visual column 64, tab-stop = 8).

COMMENT_COL = 64


def _visual_width(s: str) -> int:
    col = 0
    for ch in s:
        col = (col // 8 + 1) * 8 if ch == "\t" else col + 1
    return col


def _pad_to(s: str, target: int) -> str:
    col = _visual_width(s)
    if col >= target:
        return s + " "
    while (col // 8 + 1) * 8 <= target:
        s += "\t"
        col = (col // 8 + 1) * 8
    if col < target:
        s += " " * (target - col)
    return s


def retarget(lines: list[str], addr: int, new: str, old_named: str | None = None) -> int:
    """Replace every reference to *addr*'s label (generic SUB/LAB_ram_ADDR forms,
    plus an optional named old label) with *new*, across defs, operands and
    comments.  Returns the number of lines changed."""
    tokens = [f"SUB_ram_{addr:04x}", f"LAB_ram_{addr:04x}"]
    if old_named and not GENERIC_RE.match(old_named) and old_named != new:
        tokens.append(old_named)
    pat = re.compile(r"\b(?:" + "|".join(re.escape(t) for t in tokens) + r")\b")
    changed = 0
    for i, ln in enumerate(lines):
        if not pat.search(ln):
            continue
        if ";" in ln:
            code, _, comment = ln.partition(";")
        else:
            code, comment = ln, None
        new_code = pat.sub(new, code)
        code_changed = new_code != code
        new_comment = pat.sub(new, comment) if comment is not None else None
        if comment is None:
            lines[i] = new_code
        elif not code_changed:
            lines[i] = code + ";" + new_comment  # comment-only: keep code exactly
        else:
            lines[i] = _pad_to(new_code.rstrip("\t "), COMMENT_COL) + ";" + new_comment
        changed += 1
    return changed


# ---------------------------------------------------------------------------
# Batch: align asm labels to KB
# ---------------------------------------------------------------------------


DB_RE = re.compile(r"^(\s*DB\s+)(.*?)\s*(?:;.*)?$", re.IGNORECASE)


def _align_comment(code: str, addr: int) -> str:
    """Append a tab-aligned `; 0xADDR` comment (col 64, or the next tab stop)."""
    w = _visual_width(code)
    target = max(COMMENT_COL, (w // 8 + 1) * 8)
    return _pad_to(code, target) + f"; 0x{addr:04x}"


def find_db_span(lines: list[str], addr: int):
    """If *addr* falls strictly inside a DB line's byte range, return
    (line_idx, start_addr, prefix, tokens); else None."""
    for i, ln in enumerate(lines):
        m = DB_RE.match(ln)
        if not m:
            continue
        cm = ADDR_COMMENT_RE.search(ln)
        if not cm:
            continue
        start = int(cm.group(1), 16)
        tokens = [t.strip() for t in m.group(2).split(",") if t.strip()]
        if start < addr < start + len(tokens):
            return i, start, m.group(1), tokens
    return None


def split_db_line(lines: list[str], idx: int, start: int, prefix: str,
                  tokens: list[str], addr: int, name: str) -> None:
    """Replace the DB line at *idx* with head-DB / `name:` / tail-DB, byte-neutral."""
    k = addr - start
    head = _align_comment(prefix + ", ".join(tokens[:k]), start)
    tail = _align_comment(prefix + ", ".join(tokens[k:]), addr)
    lines[idx : idx + 1] = [head, f"{name}:", tail]


def load_kb_names(start: int, end: int) -> dict[int, str]:
    kb = load_kb(ROOT / "kb")
    return {
        e.address: e.name
        for e in kb.entries
        if start <= e.address <= end
    }


def plan_from_kb(lines: list[str], names: dict[int, str]):
    """Return (actions, warnings).  Actions are (kind, addr, name, idx)."""
    addr_idx = build_addr_index(lines)
    actions = []
    warnings = []
    for addr in sorted(names):
        name = names[addr]
        cidx = addr_idx.get(addr)
        if cidx is None:
            span = find_db_span(lines, addr)
            if span is None:
                warnings.append(f"0x{addr:04X} {name}: no content line and not inside a DB block")
                continue
            actions.append(("split", addr, name, span[0]))
            continue
        lidx = preceding_label_idx(lines, cidx)
        if lidx is None:
            actions.append(("insert", addr, name, cidx))
        else:
            cur = LABEL_RE.match(lines[lidx]).group(1)
            if cur == name:
                actions.append(("match", addr, name, lidx))
            else:
                actions.append(("rename", addr, name, lidx))
    return actions, warnings


def apply_from_kb(lines: list[str], names: dict[int, str], apply: bool):
    actions, warnings = plan_from_kb(lines, names)
    label_names = set(label_defs(lines))
    struct: list[tuple[int, str, list[str]]] = []  # (idx, op, payload) — op in insert/replace/delete
    n_rename = n_insert = n_match = n_split = n_refs = 0

    # Phase 1 — token retargeting + def renames (no line-count change; indices stay valid).
    for kind, addr, name, idx in actions:
        if kind == "match":
            n_match += 1
            n_refs += retarget(lines, addr, name)
        elif kind == "rename":
            old = LABEL_RE.match(lines[idx]).group(1)
            if name in label_names and old != name:
                warnings.append(f"0x{addr:04X}: cannot rename {old} -> {name} (name in use)")
                continue
            label_names.discard(old)
            label_names.add(name)
            n_rename += 1
            n_refs += retarget(lines, addr, name, old_named=old)
        elif kind == "insert":
            if name in label_names:
                warnings.append(f"0x{addr:04X}: cannot insert label {name} (name in use)")
                continue
            label_names.add(name)
            n_insert += 1
            n_refs += retarget(lines, addr, name)
            struct.append((idx, "insert", [f"{name}:"]))
        elif kind == "split":
            n_refs += retarget(lines, addr, name)
            span = find_db_span(lines, addr)  # re-derive after retargets
            db_idx, start, prefix, tokens = span
            k = addr - start
            head = _align_comment(prefix + ", ".join(tokens[:k]), start)
            tail = _align_comment(prefix + ", ".join(tokens[k:]), addr)
            struct.append((db_idx, "replace", [head, f"{name}:", tail]))
            # a stale copy of the label sitting on the DB block start (wrong offset)
            plab = preceding_label_idx(lines, db_idx)
            if plab is not None and LABEL_RE.match(lines[plab]).group(1) == name:
                struct.append((plab, "delete", []))
            else:
                label_names.add(name)
            n_split += 1

    # Phase 2 — structural edits, bottom-up so earlier indices stay valid.
    for idx, op, payload in sorted(struct, key=lambda x: -x[0]):
        if op == "insert":
            lines[idx:idx] = payload
        elif op == "replace":
            lines[idx : idx + 1] = payload
        elif op == "delete":
            del lines[idx]

    report = (
        f"batch: {n_rename} renamed, {n_insert} inserted, {n_split} DB-split, "
        f"{n_match} already-named; {n_refs} reference lines rewritten"
    )
    return report, warnings, (n_rename + n_insert + n_split + n_refs) > 0


# ---------------------------------------------------------------------------
# Single rename
# ---------------------------------------------------------------------------


def rename_single(lines: list[str], old: str, new: str):
    defs = label_defs(lines)
    if old not in defs:
        raise SystemExit(f"error: label {old!r} not found in {ASM.name}")
    if new in defs and defs[new] != defs[old]:
        raise SystemExit(f"error: label {new!r} already defined (line {defs[new] + 1})")
    lidx = defs[old]
    # address = the content line that follows the label
    cidx = lidx + 1
    while cidx < len(lines) and LABEL_RE.match(lines[cidx]):
        cidx += 1
    addr = content_line_addr(lines[cidx]) if cidx < len(lines) else None
    if addr is not None:
        n = retarget(lines, addr, new, old_named=old)
    else:
        # no resolvable address -> replace the literal token only
        pat = re.compile(rf"\b{re.escape(old)}\b")
        n = 0
        for i, ln in enumerate(lines):
            nl = pat.sub(new, ln)
            if nl != ln:
                lines[i] = nl
                n += 1
    return f"renamed {old} -> {new} ({n} lines)"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str]) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("old", nargs="?", help="old label name")
    ap.add_argument("new", nargs="?", help="new label name")
    ap.add_argument("--from-kb", action="store_true", help="batch-align labels to KB names")
    ap.add_argument("--start", type=lambda s: int(s, 0), default=ROM_LO)
    ap.add_argument("--end", type=lambda s: int(s, 0), default=ROM_HI)
    ap.add_argument("--apply", action="store_true", help="write changes (default: dry run)")
    args = ap.parse_args(argv)

    lines = read_lines()

    if args.from_kb:
        names = load_kb_names(args.start, args.end)
        report, warnings, changed = apply_from_kb(lines, names, args.apply)
        print(report)
        for w in warnings:
            print(f"  WARN {w}")
        if args.apply and changed:
            ASM.write_text("\n".join(lines) + "\n")
            print(f"wrote {ASM.relative_to(ROOT)}")
        elif not args.apply:
            print("(dry run — pass --apply to write)")
        return

    if not args.old or not args.new:
        ap.error("provide <old> <new>, or --from-kb")
    msg = rename_single(lines, args.old, args.new)
    ASM.write_text("\n".join(lines) + "\n")
    print(msg)
    print(f"wrote {ASM.relative_to(ROOT)}")


if __name__ == "__main__":
    main(sys.argv[1:])
