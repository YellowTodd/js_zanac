#!/usr/bin/env python3
"""Reach a base to live-verify 0x93AB (base-attack patterns) and 0x9302
(base-clear award) — sprint 0065. Warps to a late area and plays there so the
multi-segment base spawns attackers (0x8FDE reads 0x93AB round-robin) and, when
cleared, awards score via 0x91AD -> add_score (indexing 0x9302).
"""
import sys, time
sys.path.insert(0, "tools")
from zanackb.zanac_game import ZanacGame

ROUND = int(sys.argv[1]) if len(sys.argv) > 1 else 8


def main():
    with ZanacGame.launch("source/zanac.rom") as game:
        msx = game.client
        game.wait_for_title()
        # arm warp to a late, base-heavy area
        msx.cmd("set ::_wr %d" % ROUND)
        msx.cmd("set ::_wbp [debug set_bp 0x425A {} "
                "{debug write memory 0xE701 $::_wr; debug remove_bp $::_wbp}]")
        game.start_game()
        time.sleep(0.6)
        # make the ship invincible so play continues through the base
        try:
            msx.write_byte(0xE305, msx.read_byte(0xE305) | 0x80)
            msx.write_byte(0xE31B, 0xFF)
        except Exception:
            pass
        msx.cmd("set ::ba {}")   # 0x93AB descriptor ptrs (via 0x8BF5)
        msx.cmd("set ::bi 0")    # base-attack inits (0x8FE1)
        msx.cmd("set ::aw {}")   # 0x9302 award reads (counter,index)
        msx.cmd("debug set_bp 0x8FE1 {} {incr ::bi}")
        msx.cmd("debug set_bp 0x8BF5 {} {lappend ::ba [reg HL]}")
        msx.cmd("debug set_bp 0x91AD {} {lappend ::aw [list "
                "[expr {[debug read memory [expr {[reg IX]+0x57}]] & 0x1f}] "
                "[reg A]]}")
        for i in range(70):
            game.shoot_shot()
            if i % 3 == 0:
                game.steer(up=True)
            elif i % 3 == 1:
                game.steer(down=True)
            # keep invincible
            if i % 6 == 0:
                try:
                    msx.write_byte(0xE31B, 0xFF)
                    msx.write_byte(0xE305, msx.read_byte(0xE305) | 0x80)
                except Exception:
                    pass
            time.sleep(0.5)
        ba = msx.cmd("set ::ba")
        bi = msx.cmd("set ::bi")
        aw = msx.cmd("set ::aw")
        e701 = msx.read_byte(0xE701)
    hls = [int(x) for x in ba.split()] if ba.strip() else []
    inr = [h for h in hls if 0x93BB <= h <= 0x93E3]
    print("final E701 (round) =", e701)
    print("base-attack inits (0x8FE1): %s" % bi)
    print("0x8BF5 hits: %d;  HL in 0x93BB-0x93E3: %d;  sample: %s"
          % (len(hls), len(inr), ["0x%04X" % h for h in hls[:10]]))
    print("0x9302 award reads (counter&1F, index A): %s" % (aw[:200] or "(none)"))


if __name__ == "__main__":
    main()
