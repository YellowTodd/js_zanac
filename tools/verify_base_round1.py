#!/usr/bin/env python3
"""Live-verify 0x93AB (base-attack patterns) and 0x9302 (base-clear award) by
playing round 1 to its one-eye base with a permanently-invincible ship.

The round-1 base appears early; the scroll row counter (0xE702) stalls when the
base encounter is active — that's the cue. Breakpoints capture:

  0x8FE1  base-attack init count
  0x8BF5  descriptor pointer (must land in 0x93BB-0x93E3)   -> 0x93AB
  0x91AD  base-clear award: (IX+0x57)&1F counter -> index A -> 0x9302
"""
import sys, time
sys.path.insert(0, "tools")
from zanackb.zanac_game import ZanacGame

ROM = open("source/zanac.rom", "rb").read()


def rd(a):
    return ROM[a - 0x4000]


def main():
    with ZanacGame.launch("source/zanac.rom") as game:
        msx = game.client
        game.wait_for_title()
        game.start_game()
        time.sleep(0.8)
        game.make_invincible()
        msx.cmd("set ::bi 0")
        msx.cmd("set ::ba {}")
        msx.cmd("set ::aw {}")
        msx.cmd("debug set_bp 0x8FE1 {} {incr ::bi}")
        msx.cmd("debug set_bp 0x8BF5 {} {lappend ::ba [reg HL]}")
        msx.cmd("debug set_bp 0x91AD {} {lappend ::aw [list "
                "[expr {[debug read memory [expr {[reg IX]+0x57}]] & 0x1f}] "
                "[reg A]]}")
        base_seen = False
        last_row = -1
        stall = 0
        for i in range(160):                 # up to ~80 s
            game.shoot_shot()
            if base_seen:                    # rake the base eye
                game.steer(left=(i % 2 == 0), right=(i % 2 == 1))
            elif i % 6 == 0:
                game.steer(up=True)
            row = msx.read_byte(0xE702) | (msx.read_byte(0xE703) << 8)
            stall = stall + 1 if row == last_row else 0
            last_row = row
            if stall >= 4 and not base_seen:
                base_seen = True
                print("scroll stalled at row=%d (i=%d) -> base encounter" %
                      (row, i))
            time.sleep(0.5)
            if base_seen and int(msx.cmd("set ::bi")) > 0 \
                    and int(msx.cmd("llength ::aw")) >= 4:
                break
        bi = msx.cmd("set ::bi")
        ba = msx.cmd("set ::ba")
        aw = msx.cmd("set ::aw")
        e701 = msx.read_byte(0xE701)
    hls = [int(x) for x in ba.split()] if ba.strip() else []
    inr = [h for h in hls if 0x93BB <= h <= 0x93E3]
    print("round E701=%d  scroll_stalled=%s" % (e701, base_seen))
    print("base-attack inits (0x8FE1): %s" % bi)
    print("0x8BF5 descriptor hits: %d;  in 0x93BB-0x93E3: %d;  distinct ptrs: %s"
          % (len(hls), len(inr), ["0x%04X" % h for h in sorted(set(hls))[:12]]))
    print("0x9302 award reads (counter&1F, index A): %s" % (aw or "(none)"))
    if aw.strip():
        toks = aw.replace("{", " ").replace("}", " ").split()
        seen = set()
        for j in range(0, len(toks) - 1, 2):
            c, a = int(toks[j]), int(toks[j + 1])
            if c in seen:
                continue
            seen.add(c)
            exp = rd(0x9302 + c) if c <= 0x12 else None
            print("   counter=%d -> A=%d  (ROM 0x9302[%d]=%s)%s"
                  % (c, a, c, exp, "  MATCH" if exp == a else "  <<MISMATCH"))


if __name__ == "__main__":
    main()
