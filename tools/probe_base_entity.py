#!/usr/bin/env python3
"""Find the round-1 base entity in the table during the scroll stall: dump
enemy slots (0xE300 + i*32) so we can learn the base core's type/X/Y/HP fields
and how (IX+0x57) / the clear path is driven.
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
        last = -1
        stall = 0
        seen = False
        for i in range(160):
            game.shoot_shot()
            if i % 6 == 0:
                game.steer(up=True)
            row = msx.read_byte(0xE702) | (msx.read_byte(0xE703) << 8)
            stall = stall + 1 if row == last else 0
            last = row
            if stall >= 4:
                seen = True
                break
            time.sleep(0.5)
        print("stalled=%s row=%d" % (seen, last))
        ship = bytes(msx.read_memory(0xE300, 8))
        print("ship slot0 0xE300:", ship.hex(), " X=E301=%d Y=E302=%d"
              % (ship[1], ship[2]))
        for s in range(5, 25):
            base = 0xE300 + s * 32
            slot = bytes(msx.read_memory(base, 32))
            if slot[0] == 0:
                continue
            print("slot%2d 0x%04X type=0x%02X X=%d Y=%d  +18=%02X +19(hp)=%02X "
                  "+50=%02X +51=%02X +57=%02X"
                  % (s, base, slot[0], slot[1], slot[2], slot[0x18],
                     slot[0x19], slot[0x50] if len(slot) > 0x50 else 0,
                     slot[0x51] if len(slot) > 0x51 else 0,
                     slot[0x57] if len(slot) > 0x57 else 0))
        # also dump the global base controller state at 0xE150 area
        g = bytes(msx.read_memory(0xE150, 16))
        print("E150:", g.hex())


if __name__ == "__main__":
    main()
