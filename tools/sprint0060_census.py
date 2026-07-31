#!/usr/bin/env python3
"""Sprint 0060 — live per-round idol census.

For each round, warp there (force E701 at the 0x425A title bp), make the ship
invincible, drop speed throttle, and install a NON-breaking logging breakpoint at
0x87C3 inside handler_type70_wide_structure. That point runs once per idol, after
its +0x1C/1D warp field is loaded from the 0xE720 idol table and just before
+0x03 (the table index) is overwritten with the tile pattern. We log, per idol:

    slot, type(+0x00), subtype(+0x18), idx(+0x03), dest(+0x1D<<8|+0x1C), Y(+1), X(+2)

Then classify the destination via resolve_round_from_ptr and the destruction
sub-type branch (0x880D) into: normal / orb(kill-all) / WARP idol.

Run: .venv/bin/python tools/sprint0060_census.py [round]   (default: all 0..8)
"""
import os, sys, time, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from zanackb.zanac_game import ZanacGame

ROM = open(pathlib.Path(__file__).resolve().parent.parent / "source/zanac.rom", "rb").read()
def rom_w(a): return ROM[a - 0x4000] | (ROM[a - 0x4000 + 1] << 8)
TBL = [rom_w(0x945C + i * 2) for i in range(9)]
def resolve(ptr):
    for i in range(8):
        if ptr >= TBL[i]:
            return 8 - i
    return 0
STARTS = {rom_w(0x945C + i * 2): (8 - i) for i in range(8)}
STARTS[0xA65C] = 0

# types whose handler runs the 0x87B0 table read → +0x1C/1D is freshly loaded
# from the 0xE720 idol table. Types 84-86 join handler_type70 at 0x87C3 and do
# NOT read the table, so their +0x1C/1D at the bp is stale (ignore for dest).
TABLE_TYPES = {70, 71, 81, 82, 87, 88, 89}


def census_round(game, r):
    msx = game.client
    # warp: one-shot bp forcing E701=r at 0x425A
    msx.cmd("debug break"); msx.cmd("set ::h 0")
    wbp = msx.cmd("debug set_bp 0x425A {} "
                  "{ debug write memory 0xE701 %d; incr ::h; debug cont }" % r)
    msx.cont()
    game.wait_for_title(); game.start_game()
    time.sleep(1.0)
    try: game.make_invincible()
    except Exception: pass
    # logging bp at 0x87C3 (non-breaking)
    msx.cmd("set ::idols {}")
    lbp = msx.cmd(r"""debug set_bp 0x87C3 {} {
        set ix [reg IX]
        lappend ::idols [list $ix [debug read memory $ix] \
            [debug read memory [expr {$ix+0x18}]] \
            [debug read memory [expr {$ix+0x03}]] \
            [debug read memory [expr {$ix+0x1c}]] \
            [debug read memory [expr {$ix+0x1d}]] \
            [debug read memory [expr {$ix+0x01}]] \
            [debug read memory [expr {$ix+0x02}]] \
            [debug read memory 0xE701]]
    }""")
    msx.cmd("set throttle off")
    # run in chunks; stop when round advances past r, on a LONG plateau, or cap.
    # round 7 LOOPS on itself (E701 stays 7). Budget tuned so late (high-idx)
    # totems get to activate before we stop.
    budget = int(os.environ.get("CENSUS_CHUNKS", "40"))
    plateau = int(os.environ.get("CENSUS_PLATEAU", "12"))
    last_n, stagnant = 0, 0
    for i in range(budget):
        if not msx.is_running():
            msx.cont()
        time.sleep(2.0)
        cur = msx.read_byte(0xE701)
        if cur != r and cur != 0:      # advanced/warped to another round
            break
        n = len(_split_tcl(msx.cmd("set ::idols")))
        stagnant = stagnant + 1 if n == last_n else 0
        last_n = n
        if stagnant >= plateau:        # long stall → done scrolling
            break
    msx.cmd("set throttle on")
    raw = msx.cmd("set ::idols")
    try: msx.remove_breakpoint(lbp)
    except Exception: pass
    try: msx.remove_breakpoint(wbp)
    except Exception: pass
    # parse TCL list of lists
    idols = []
    for tok in _split_tcl(raw):
        vals = [int(x) for x in tok.split()]
        if len(vals) == 9:
            idols.append(vals)
    return idols


def _split_tcl(s):
    """Split a TCL list whose elements are brace-wrapped sublists."""
    out, depth, cur = [], 0, ""
    for ch in s:
        if ch == "{":
            depth += 1
            if depth == 1:
                cur = ""; continue
        if ch == "}":
            depth -= 1
            if depth == 0:
                out.append(cur); continue
        if depth >= 1:
            cur += ch
    return out


def main():
    rounds = [int(sys.argv[1])] if len(sys.argv) > 1 else list(range(9))
    with ZanacGame.launch("source/zanac.rom") as game:
        game.wait_for_title()
        for r in rounds:
            idols = census_round(game, r)
            # keep only idols captured while the LIVE round (v[8]) == requested r
            idols = [v for v in idols if v[8] == r]
            # dedupe identical (type,sub,idx,dest,Y,X)
            uniq, seen = [], set()
            for v in idols:
                key = tuple(v[1:8])
                if key not in seen:
                    seen.add(key); uniq.append(v)
            realwarp, r0warp = [], []
            for slot, typ, sub, idx, lo, hi, y, x, _e in uniq:
                t = typ & 0x7f
                if t not in TABLE_TYPES:
                    continue
                dest = (hi << 8) | lo
                if 0xA65C <= dest <= 0xB7A5:
                    realwarp.append((t, sub, idx, dest, resolve(dest),
                                     dest in STARTS, y, x))
                elif dest < 0xA65C:
                    r0warp.append((t, sub, idx, dest, y, x))
            print(f"\n===== ROUND {r} : {len(uniq)} idol activations "
                  f"({len(realwarp)} real-round warps, {len(r0warp)} →R0) =====")
            if realwarp:
                print("  REAL-ROUND warp idols (dest = stream pointer):")
                for t, s, idx, d, rnd, st, y, x in sorted(realwarp, key=lambda z: z[3]):
                    print(f"    type {t:2d} +18=0x{s:02X} idx={idx:3d} "
                          f"-> 0x{d:04X} = round {rnd}{'*' if st else '(mid)'} "
                          f"@Y{y}/X{x}")
            # orb-spawning types (70/71) whose dest is a PLAUSIBLE map pointer
            # (>=0xA000) resolving to round 0 = candidate SECRET round-0 totems.
            # (small dests like 0x0104 resolve to R0 too but point at RAM/garbage.)
            orb0 = [z for z in r0warp if z[0] in (70, 71) and z[3] >= 0xA000]
            seen2 = set(); u0 = []
            for z in orb0:
                k = (z[0], z[2], z[3], z[4], z[5])
                if k not in seen2:
                    seen2.add(k); u0.append(z)
            if u0:
                print("  *** SECRET round-0 totems (type 70/71, dest=map ptr → R0):")
                for t, s, idx, d, y, x in u0:
                    print(f"    type {t:2d} idx={idx:3d} -> 0x{d:04X} "
                          f"= round {resolve(d)} @Y{y}/X{x}")
            # also report the count of incidental small-dest orb idols
            n_small = len({(z[0], z[2], z[3]) for z in r0warp
                           if z[0] in (70, 71) and z[3] < 0xA000})
            print(f"  ({n_small} type-70/71 idols with small/garbage dest → R0 incidental)")
            # type-82 fire dispensers (digit = fire type)
            fires = sorted({(z[2], z[3] & 0xFF) for z in r0warp
                            if z[0] == 82})
            if fires:
                print("  type-82 fire dispensers (idx: fire# digit): "
                      + ", ".join(f"idx{idx}:'{d}'" for idx, d in fires[:12]))


if __name__ == "__main__":
    main()
