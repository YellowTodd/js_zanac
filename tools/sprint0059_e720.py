#!/usr/bin/env python3
"""Sprint 0059 — read the live per-round idol table pointer (0xE720) for every
round, then decode each table for embedded warp-destination stream pointers.

For each round r in 0..8: warp (force E701=r at the 0x425A title bp), start,
let the round-start map-script cmd 8 fire (it stores its operand -> E720), read
E720, and dump the ROM table there. Any 2-byte LE value inside the table that
resolves (via resolve_round_from_ptr) to a valid round is a warp destination.

Run: .venv/bin/python tools/sprint0059_e720.py
"""
import sys, time, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from zanac_shot import ShotSession

ROM = open(pathlib.Path(__file__).resolve().parent.parent / "source/zanac.rom", "rb").read()
def rom_at(a, n): return ROM[a - 0x4000:a - 0x4000 + n]
def rom_w(a): return ROM[a - 0x4000] | (ROM[a - 0x4000 + 1] << 8)

TBL = [rom_w(0x945C + i * 2) for i in range(9)]      # entries 0..7 = rounds 8..1
def resolve(ptr):
    for i in range(8):
        if ptr >= TBL[i]:
            return 8 - i
    return 0

STREAM_STARTS = {rom_w(0x945C + i * 2): (8 - i) for i in range(8)}
STREAM_STARTS[rom_w(0x946C)] = 0                     # 0xA65C -> round 0


def warp_read_e720(round_no):
    with ShotSession() as s:
        msx = s.msx
        msx.cmd("debug break")
        msx.cmd("set ::h 0")
        bp = msx.cmd("debug set_bp 0x425A {} "
                     "{ debug write memory 0xE701 %d; incr ::h; debug cont }" % round_no)
        msx.cont()
        time.sleep(8.0)
        for _ in range(6):
            msx.key_down(8, 0x01); time.sleep(0.4); msx.key_up(8, 0x01); time.sleep(0.4)
            if int(msx.cmd("set ::h")) > 0:
                break
        time.sleep(2.5)                              # let cmd 8 fire at round start
        e720 = msx.read_byte(0xE720) | (msx.read_byte(0xE721) << 8)
        e701 = msx.read_byte(0xE701)
        try: msx.remove_breakpoint(bp)
        except Exception: pass
        return e701, e720


def main():
    print("stream starts:", {f"0x{k:04X}": v for k, v in sorted(STREAM_STARTS.items())})
    for r in range(9):
        e701, e720 = warp_read_e720(r)
        line = f"\n=== warp round {r}: E701={e701}  E720=0x{e720:04X} ==="
        print(line)
        if not (0xA000 <= e720 <= 0xBE00):
            print("  (E720 not in map-data range; skipped)")
            continue
        tbl = rom_at(e720, 56)
        print("  bytes:", tbl.hex())
        hits = []
        for off in range(len(tbl) - 1):
            v = tbl[off] | (tbl[off + 1] << 8)
            if v in STREAM_STARTS:
                hits.append((off, v, STREAM_STARTS[v]))
        for off, v, rd in hits:
            print(f"    +{off:2d}: 0x{v:04X} = round-{rd} stream start  (WARP DEST)")
        if not hits:
            print("    (no exact stream-start pointers found in first 56 bytes)")


if __name__ == "__main__":
    main()
