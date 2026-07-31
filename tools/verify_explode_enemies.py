#!/usr/bin/env python3
"""Confirm explode_enemies (0x8A26) fires on a base clear and converts living
enemies to explosion type 0x23 (sprint 0067). Reuses the round-1 base fight.
"""
import sys, time
sys.path.insert(0, "tools")
from zanackb.zanac_game import ZanacGame


def main():
    with ZanacGame.launch("source/zanac.rom") as game:
        msx = game.client
        game.wait_for_title()
        game.start_game()
        time.sleep(0.8)
        game.make_invincible()
        # count explode_enemies entries; snapshot enemy type bytes at entry
        msx.cmd("set ::ex 0")
        msx.cmd("set ::snap {}")
        msx.cmd("debug set_bp 0x8A26 {} {incr ::ex; if {$::ex<=2} {"
                "set s {}; for {set i 5} {$i<25} {incr i} {"
                "lappend s [debug read memory [expr {0xE300+$i*32}]]}; "
                "lappend ::snap $s}}")
        last = -1
        stall = 0
        base_seen = False
        for i in range(200):
            game.shoot_shot()
            for a, v in [(0xE10B, 5), (0xE10D, 2), (0xE10E, 0x0A), (0xE10F, 0x30)]:
                try:
                    msx.write_byte(a, v)
                except Exception:
                    pass
            row = msx.read_byte(0xE702) | (msx.read_byte(0xE703) << 8)
            stall = stall + 1 if row == last else 0
            last = row
            if stall >= 4 and not base_seen:
                base_seen = True
                print("base encounter (row %d)" % row)
            if base_seen:
                e152 = msx.read_byte(0xE152)
                sx = msx.read_byte(0xE301)
                for tx in (60, 100, 140, 180, 100, 60):
                    pass
                game.steer(left=(i % 2 == 0), right=(i % 2 == 1))
                if i % 3 == 0 and 0 < e152 <= 2:
                    msx.write_byte(0xE152, 0)
            time.sleep(0.4)
            if int(msx.cmd("set ::ex")) > 0 and base_seen:
                # let a couple more frames pass so 0x23 conversion is visible
                time.sleep(0.3)
                break
        ex = msx.cmd("set ::ex")
        snap = msx.cmd("set ::snap")
        # read enemy types now (after explode)
        after = [msx.read_byte(0xE300 + i * 32) & 0x7F for i in range(5, 25)]
    print("explode_enemies (0x8A26) entries: %s" % ex)
    print("enemy type bytes captured at 1st entry (masked view in snap):")
    print("  snap:", snap[:250])
    print("enemy types (0x7F-masked) shortly after:", [hex(t) for t in after])
    n23 = sum(1 for t in after if t == 0x23)
    print("slots now = explosion 0x23: %d" % n23)


if __name__ == "__main__":
    main()
