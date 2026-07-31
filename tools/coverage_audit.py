"""Sprint 0063 — byte-coverage audit for source/zanac.asm.

Classifies every ROM byte 0x4000-0xBFFF:

  code         instruction line (address comment, not a DB)
  data-kb      DB byte inside the extent of a KB entry (address[..end])
  data-inline  DB run immediately following a CALL into the inline
               VRAM string-print family (0x5C10/0x5C1F/0x5C25/0x5C28)
  unknown      everything else

Outputs per-class totals and the exact unknown ranges with the nearest
labels before/after. Also sanity-checks the KB against the asm.

Run: .venv/bin/python tools/coverage_audit.py [--all-ranges]
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASM = ROOT / "source" / "zanac.asm"
ROM_LO, ROM_HI = 0x4000, 0xC000        # [lo, hi)
# inline VRAM string-print family + the inline DW-dispatch helper 0x5C2E
INLINE_PRINT = {0x5C10, 0x5C1F, 0x5C25, 0x5C28, 0x5C2E}

ADDR_RE = re.compile(r";\s*0x([0-9A-Fa-f]{4})\b")
LABEL_RE = re.compile(r"^(\w+):")
DB_RE = re.compile(r"^\s*DB\b")
DW_RE = re.compile(r"^\s*DW\b")
BYTE_RE = re.compile(r"0x([0-9A-Fa-f]{2})\b")
WORD_RE = re.compile(r"0x([0-9A-Fa-f]{4})\b")
STR_RE = re.compile(r'"([^"]*)"')
CALL_RE = re.compile(r"\bCALL\s+0x([0-9A-Fa-f]{4})", re.IGNORECASE)
FM_FIELD = re.compile(r"^(\w+):\s*(.+?)\s*$")


def parse_asm():
    """Return (lines, labels) where lines is a sorted list of dicts:
    {addr, kind: 'code'|'db', nbytes (db only), lineno, after_print_call}."""
    items, labels = [], []
    pending_print = False
    for lineno, raw in enumerate(ASM.read_text(encoding="utf-8").splitlines(), 1):
        code_part = raw.split(";")[0]
        comment = raw[len(code_part):]
        lm = LABEL_RE.match(code_part)
        if lm:
            labels.append((lineno, lm.group(1)))
            continue
        if not code_part.strip():
            continue                            # comment-only / blank line
        am = ADDR_RE.search(comment)
        if not am:
            continue
        addr = int(am.group(1), 16)
        if not (ROM_LO <= addr < ROM_HI):
            continue
        inline = "inline" in comment            # "inline string/table for 0xNNNN"
        if DB_RE.match(code_part):
            body = code_part.split("DB", 1)[1]
            hexbytes = BYTE_RE.findall(STR_RE.sub("", body))
            nb = len(hexbytes) + sum(len(s) for s in STR_RE.findall(body))
            all_ff = bool(hexbytes) and nb == len(hexbytes) and \
                all(b.upper() == "FF" for b in hexbytes)
            items.append({"addr": addr, "kind": "db", "nbytes": nb,
                          "lineno": lineno, "all_ff": all_ff,
                          "after_print": pending_print or inline})
            # a DB run after a print call stays inline until code resumes
        elif DW_RE.match(code_part):
            nw = len(WORD_RE.findall(code_part.split("DW", 1)[1]))
            items.append({"addr": addr, "kind": "db", "nbytes": 2 * nw,
                          "lineno": lineno,
                          "after_print": pending_print or inline})
        else:
            cm = CALL_RE.search(code_part)
            tgt = int(cm.group(1), 16) if cm else None
            pending_print = tgt in INLINE_PRINT
            items.append({"addr": addr, "kind": "code",
                          "lineno": lineno, "after_print": False})
    items.sort(key=lambda d: d["addr"])
    return items, labels


def parse_kb():
    """Return list of (address, end_inclusive_or_None, kind, name, path)."""
    entries = []
    for md in list((ROOT / "kb" / "symbols").rglob("*.md")) + \
              list((ROOT / "kb" / "data").glob("*.md")):
        text = md.read_text(encoding="utf-8")
        if not text.startswith("---"):
            continue
        fm = text.split("---", 2)[1]
        fields = {}
        for line in fm.splitlines():
            m = FM_FIELD.match(line)
            if m:
                fields[m.group(1)] = m.group(2).strip('"')
        try:
            addr = int(fields.get("address", ""), 16)
        except ValueError:
            continue
        end = None
        if "end" in fields:
            try:
                end = int(fields["end"], 16)
            except ValueError:
                pass
        entries.append((addr, end, fields.get("kind", "?"),
                        fields.get("name", md.stem), md))
    return entries


def main():
    show_all = "--all-ranges" in sys.argv
    items, labels = parse_asm()
    kb = parse_kb()

    # ---- lay out the byte map -------------------------------------------
    classes = bytearray(b"\x00" * (ROM_HI - ROM_LO))   # 0=unknown
    C_CODE, C_KB, C_INLINE, C_PAD, C_UNKNOWN = 1, 2, 3, 4, 0
    NAMES = {1: "code", 2: "data-kb", 3: "data-inline", 4: "padding",
             0: "unknown"}

    problems = []
    for i, it in enumerate(items):
        start = it["addr"]
        nxt = items[i + 1]["addr"] if i + 1 < len(items) else ROM_HI
        if it["kind"] == "code":
            span = nxt - start
            if span <= 0 or span > 4:
                problems.append(f"code line {it['lineno']} @0x{start:04X}: "
                                f"span {span} (next 0x{nxt:04X})")
                span = max(1, min(span, 4))
            cls = C_CODE
        else:
            span = it["nbytes"]
            if start + span != nxt and nxt != ROM_HI:
                problems.append(f"DB line {it['lineno']} @0x{start:04X}: "
                                f"{span} bytes but next line @0x{nxt:04X}")
            if it["after_print"]:
                cls = C_INLINE
            elif it.get("all_ff") and span <= 16:
                cls = C_PAD          # 0xFF filler between routines / ROM tail
            else:
                cls = C_UNKNOWN
        for a in range(start, min(start + span, ROM_HI)):
            classes[a - ROM_LO] = cls

    # ---- overlay KB extents on data bytes -------------------------------
    kb_missing_in_asm = []
    addr_set = {it["addr"] for it in items}
    for addr, end, kind, name, path in kb:
        if not (ROM_LO <= addr < ROM_HI):
            continue
        if addr not in addr_set:
            kb_missing_in_asm.append((addr, name))
        hi = (end + 1) if end is not None else None
        if hi is None:
            # no end: cover the contiguous DB run starting at addr (if any)
            hi = addr
            for it in items:
                if it["addr"] == hi and it["kind"] == "db":
                    hi += it["nbytes"]
                elif it["addr"] > hi:
                    break
            if hi == addr:
                continue                       # routine without end: code
        for a in range(addr, min(hi, ROM_HI)):
            if classes[a - ROM_LO] in (C_UNKNOWN, C_INLINE):
                classes[a - ROM_LO] = C_KB

    # ---- report ----------------------------------------------------------
    total = ROM_HI - ROM_LO
    counts = {c: classes.count(c)
              for c in (C_CODE, C_KB, C_INLINE, C_PAD, C_UNKNOWN)}
    print(f"ROM 0x{ROM_LO:04X}-0x{ROM_HI - 1:04X}  ({total} bytes)")
    for c in (C_CODE, C_KB, C_INLINE, C_PAD, C_UNKNOWN):
        print(f"  {NAMES[c]:<12} {counts[c]:6d}  {100.0 * counts[c] / total:6.2f}%")
    known = total - counts[C_UNKNOWN]
    print(f"  {'KNOWN':<12} {known:6d}  {100.0 * known / total:6.2f}%")

    # unknown ranges with nearest labels
    lbl_by_line = sorted(labels)
    line_by_addr = {it["addr"]: it["lineno"] for it in items}

    def nearest_labels(addr):
        ln = None
        for a in sorted(line_by_addr):
            if a <= addr:
                ln = line_by_addr[a]
            else:
                break
        before = after = "?"
        if ln is not None:
            before_c = [n for l, n in lbl_by_line if l <= ln]
            after_c = [n for l, n in lbl_by_line if l > ln]
            before = before_c[-1] if before_c else "?"
            after = after_c[0] if after_c else "?"
        return before, after

    print("\nUnknown ranges:")
    a = ROM_LO
    ranges = []
    while a < ROM_HI:
        if classes[a - ROM_LO] == C_UNKNOWN:
            b = a
            while b < ROM_HI and classes[b - ROM_LO] == C_UNKNOWN:
                b += 1
            ranges.append((a, b))
            a = b
        else:
            a += 1
    for lo, hi in ranges:
        if hi - lo < 4 and not show_all:
            continue
        bef, aft = nearest_labels(lo)
        print(f"  0x{lo:04X}-0x{hi - 1:04X}  {hi - lo:5d} B   "
              f"after {bef} / before {aft}")
    small = sum(hi - lo for lo, hi in ranges if hi - lo < 4)
    nsmall = sum(1 for lo, hi in ranges if hi - lo < 4)
    if not show_all and nsmall:
        print(f"  (+ {nsmall} ranges <4 B totalling {small} B; --all-ranges)")

    if kb_missing_in_asm:
        print("\nKB addresses with no matching asm line (mid-run or stale):")
        for addr, name in sorted(kb_missing_in_asm):
            print(f"  0x{addr:04X}  {name}")
    if problems:
        print(f"\nParser warnings ({len(problems)}):")
        for p in problems[:20]:
            print("  " + p)

    print(f"\nSanity: bytes mapped = {sum(counts.values())} (expect {total})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
