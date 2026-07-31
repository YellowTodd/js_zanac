#!/usr/bin/env python3
"""Destroy the round-1 base to fire the base-clear award reader (0x91AD -> 0x9302).

The base is a row of segments; each segment killed (HP +0x19 -> 0) decrements
E152 at 0x8BB4, and when E152 == 0 the controller runs the clear routine
(0x9165 -> 0x91A9) that reads 0x9302[(E157)&0x1F] and awards score.

Strategy: invincible + boosted ship; once the scroll stalls (base encounter),
sweep the full screen width while holding fire so shots rake every segment
column. Monitor E152; if it is nearly cleared but stalls, finish the last
segment (poke E152=0) so the authentic clear reader executes. Verify the
0x91AD-loaded index equals ROM 0x9302[counter].
"""
import sys, time
sys.path.insert(0, "tools")
from zanackb.zanac_game import ZanacGame

ROM = open("source/zanac.rom", "rb").read()


def rd(a):
    return ROM[a - 0x4000]


def boost(msx):
    for a, v in [(0xE10B, 0x05), (0xE10D, 0x02), (0xE10E, 0x0A), (0xE10F, 0x30)]:
        try:
            msx.write_byte(a, v)
        except Exception:
            pass


def main():
    with ZanacGame.launch("source/zanac.rom") as game:
        msx = game.client
        game.wait_for_title()
        game.start_game()
        time.sleep(0.8)
        game.make_invincible()
        msx.cmd("set ::aw {}")
        # break at 0x91AE (AFTER the LD A,(HL) at 0x91AD) so reg A = loaded index
        msx.cmd("debug set_bp 0x91AE {} {lappend ::aw [list "
                "[expr {[debug read memory [expr {[reg IX]+0x57}]] & 0x1f}] "
                "[reg A]]}")
        last = -1
        stall = 0
        base_seen = None
        e152_hist = []
        sweep_x = [20, 60, 100, 140, 180, 220]
        si = 0
        for i in range(200):
            game.shoot_shot()
            boost(msx)
            row = msx.read_byte(0xE702) | (msx.read_byte(0xE703) << 8)
            stall = stall + 1 if row == last else 0
            last = row
            if stall >= 4 and base_seen is None:
                base_seen = i
                print("scroll stalled row=%d (i=%d) -> base; sweeping" %
                      (row, i))
            if base_seen is not None:
                e152 = msx.read_byte(0xE152)
                e152_hist.append(e152)
                # full-width sweep: nudge ship toward the next sweep column
                tx = sweep_x[si % len(sweep_x)]
                sx = msx.read_byte(0xE301)
                if sx < tx - 6:
                    game.steer(right=True)
                elif sx > tx + 6:
                    game.steer(left=True)
                else:
                    si += 1
                # after enough base-time, if segments nearly gone, finish it
                secs = i - base_seen
                if secs >= 40 and 0 < e152 <= 2:
                    print("forcing final segment: E152 %d -> 0" % e152)
                    msx.write_byte(0xE152, 0)
                if int(msx.cmd("llength ::aw")) >= 2:
                    print("award reader fired")
                    break
            elif i % 6 == 0:
                game.steer(up=True)
            time.sleep(0.4)
        aw = msx.cmd("set ::aw")
        e701 = msx.read_byte(0xE701)
    print("round E701=%d  base at i=%s" % (e701, base_seen))
    if e152_hist:
        print("E152 range observed: max=%d min=%d  (segment count -> 0 = clear)"
              % (max(e152_hist), min(e152_hist)))
    print("0x9302 award reads (counter&1F -> index A):")
    if aw.strip():
        toks = aw.replace("{", " ").replace("}", " ").split()
        seen = set()
        for j in range(0, len(toks) - 1, 2):
            c, a = int(toks[j]), int(toks[j + 1])
            if (c, a) in seen:
                continue
            seen.add((c, a))
            exp = rd(0x9302 + c) if c <= 0x12 else None
            print("   counter=%2d -> loaded A=%2d   ROM 0x9302[%d]=%s   %s"
                  % (c, a, c, exp, "MATCH" if exp == a else "MISMATCH"))
    else:
        print("   (none)")


if __name__ == "__main__":
    main()
