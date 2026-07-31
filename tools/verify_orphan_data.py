#!/usr/bin/env python3
"""Live verification for sprint 0065 orphan-data tables.

Drives gameplay with continuous fire (triggers ALC waves, ground structures and
bases), while non-halting breakpoints log every read of the four tables, and a
read-watchpoint covers dir8_delta_table (0x7748-0x7757). Then reports:

  - data_4b2a (0x4B2A): (IX+0x18) sub-type -> award index A  @0x4A73
  - 0x9302 base-clear award index: (IX+0x57)&1F -> A          @0x91AD
  - 0x93AB base-attack: HL descriptor ptr must be in table     @0x8BF5
  - dir8_delta_table: any read = has a reader; none = dead     wp 0x7748
"""
import sys, time
sys.path.insert(0, "tools")
from zanackb.zanac_game import ZanacGame, MSXKey

ROM = open("source/zanac.rom", "rb").read()


def rd(a, n=1):
    return ROM[a - 0x4000:a - 0x4000 + n]


def main():
    with ZanacGame.launch("source/zanac.rom") as game:
        msx = game.client
        game.wait_for_title()
        game.start_game()
        time.sleep(0.5)
        # non-halting logging breakpoints
        msx.cmd("set ::t4b {}")   # data_4b2a: sub-type + index
        msx.cmd("set ::t93 {}")   # 0x9302: counter + index
        msx.cmd("set ::tba {}")   # 0x93AB: descriptor ptr
        # data_4b2a: at 0x4A74 (after LD A,(HL)) A = award index; log sub + A.
        bp1 = msx.cmd("debug set_bp 0x4A74 {} "
                      "{lappend ::t4b [list [debug read memory "
                      "[expr {[reg IX]+0x18}]] [reg A]]}")
        bp2 = msx.cmd("debug set_bp 0x91AD {} "
                      "{lappend ::t93 [list [expr {[debug read memory "
                      "[expr {[reg IX]+0x57}]] & 0x1f}] [reg A]]}")
        # 0x93AB base-attack: break just after HL loaded from the table @0x8FF7
        bp3 = msx.cmd("debug set_bp 0x8BF5 {} {lappend ::tba [reg HL]}")
        msx.cmd("set ::binit 0")
        bp4 = msx.cmd("debug set_bp 0x8FE1 {} {incr ::binit}")  # base-attack init
        # read-watchpoint over dir8_delta_table
        msx.cmd("set ::dir8 0")
        wp = msx.cmd("debug set_watchpoint read_mem {0x7748 0x7757} {} "
                     "{incr ::dir8; set ::dir8pc [reg PC]}")
        # drive: hold fire + weave, ~45 s of real time to reach a base
        for i in range(90):
            game.shoot_shot()
            if i % 4 == 0:
                game.steer(up=True)
            elif i % 4 == 2:
                game.steer(down=True)
            time.sleep(0.5)
        t4b = msx.cmd("set ::t4b")
        t93 = msx.cmd("set ::t93")
        tba = msx.cmd("set ::tba")
        binit = msx.cmd("set ::binit")
        dir8 = msx.cmd("set ::dir8")
        dir8pc = msx.cmd("set ::dir8pc") if dir8 != "0" else "-"
        print("base-attack inits (0x8FE1): %s" % binit)
        for b in (bp1, bp2, bp3, bp4):
            try:
                msx.cmd("debug remove_bp %s" % b)
            except Exception:
                pass
        try:
            msx.cmd("debug remove_watchpoint %s" % wp)
        except Exception:
            pass

    print("=== data_4b2a (0x4B2A) reads @0x4A6F/0x4A73 ===")
    print(" raw:", t4b[:300])
    print("=== 0x9302 base-clear award reads @0x91AD ===")
    print(" raw:", t93[:300])
    print("=== 0x93AB base-attack descriptor ptrs @0x8BF5 (HL, decimal) ===")
    hls = [int(x) for x in tba.split()] if tba.strip() else []
    in_range = [h for h in hls if 0x93BB <= h <= 0x93E3]
    print(" %d hits; in-table [0x93BB-0x93E3]: %d; sample: %s"
          % (len(hls), len(in_range),
             ["0x%04X" % h for h in hls[:8]]))
    print("=== dir8_delta_table (0x7748-0x7757) read-watchpoint ===")
    print(" reads: %s  (PC=%s)" % (dir8, dir8pc))
    print("   -> %s" % ("HAS READER" if dir8 != "0" else "no reads = dead data"))


if __name__ == "__main__":
    main()
