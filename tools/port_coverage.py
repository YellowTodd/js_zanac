"""How much of the ROM's *code* the JavaScript port actually reproduces.

Method: the port cites the ROM address of nearly every routine it implements
in its comments (`0x8A5A`, `// 0x76E9`, ...). Cross-referencing those against
the KB's routine ranges gives a defensible lower bound on ported code bytes -
"defensible" because a citation is only written when the routine was read and
implemented, and a lower bound because a ported routine with no citation
counts as missing.

    python tools/port_coverage.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from coverage_audit import parse_asm, parse_kb  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PORT = ROOT / "web" / "src"
ROM_BASE, ROM_END = 0x4000, 0xC000

HEX = re.compile(r"0x([0-9a-fA-F]{4})")


def cited_addresses() -> set[int]:
    seen: set[int] = set()
    for js in PORT.rglob("*.js"):
        for m in HEX.finditer(js.read_text(encoding="utf-8")):
            v = int(m.group(1), 16)
            if ROM_BASE <= v < ROM_END:
                seen.add(v)
    return seen


def main() -> None:
    items, _ = parse_asm()
    # Byte-level code mask, same rule coverage_audit uses.
    code = bytearray(ROM_END - ROM_BASE)
    for i, item in enumerate(items):
        if item["kind"] != "code":
            continue
        start = item["addr"]
        nxt = items[i + 1]["addr"] if i + 1 < len(items) else ROM_END
        for a in range(start, min(nxt, ROM_END)):
            code[a - ROM_BASE] = 1

    # parse_kb -> [(address, end, kind, name, path), ...]. Roughly a fifth of
    # the routine entries have no `end:`; for those, run to the next symbol so
    # their bodies are attributed instead of vanishing from the denominator.
    raw = [
        (addr, end, name)
        for addr, end, kind, name, _path in parse_kb()
        if kind == "routine" and ROM_BASE <= addr < ROM_END
    ]
    bounds = sorted({a for a, _e, _n in raw} | {s for s, _e, _n in
                    [(x[0], x[1], x[2]) for x in raw]} | {ROM_END})
    starts = sorted({a for a, _e, _n in raw}) + [ROM_END]
    routines = []
    for addr, end, name in raw:
        if end and end > addr:
            hi = end
        else:
            nxt = next((s for s in starts if s > addr), ROM_END)
            hi = nxt
        routines.append((addr, min(hi, ROM_END), name))
    del bounds

    cited = cited_addresses()
    total_code = sum(code)
    ported_bytes = 0
    ported, missing = [], []
    covered = bytearray(ROM_END - ROM_BASE)

    for start, end, name in sorted(routines):
        size = sum(code[a - ROM_BASE] for a in range(start, end))
        # A routine counts as ported when the port cites any address inside it.
        hit = any(a in cited for a in range(start, end))
        if hit:
            ported.append((name, size))
            for a in range(start, end):
                if code[a - ROM_BASE]:
                    covered[a - ROM_BASE] = 1
        elif size:
            missing.append((size, name, start, end))

    ported_bytes = sum(covered)
    unattributed = total_code - sum(
        1
        for a in range(ROM_BASE, ROM_END)
        if code[a - ROM_BASE]
        and any(s <= a < e for s, e, _ in routines)
    )

    print(f"ROM code bytes            {total_code:6d}")
    print(f"  in a KB routine, ported {ported_bytes:6d}  {ported_bytes/total_code:6.1%}")
    rest = total_code - ported_bytes
    print(f"  not attributed as ported{rest:6d}  {rest/total_code:6.1%}")
    print(f"    of which outside any KB routine range: {unattributed}")
    print()
    print("Largest unported KB routines:")
    for size, name, start, end in sorted(missing, reverse=True)[:25]:
        print(f"  {size:5d}  0x{start:04X}-0x{end:04X}  {name}")


if __name__ == "__main__":
    main()
