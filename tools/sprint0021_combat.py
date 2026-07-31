"""Sprint 0021 — second pass: entity slot 0 vs 0xE100 comparison under combat."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from zanackb.zanac_game import ZanacGame

ENTITY_BASE = 0xE300
SLOT_SIZE   = 32
E100_BASE   = 0xE100


def hex32(data: bytes, base: int = 0) -> str:
    offs = " ".join(f"+{base+i:02X}" for i in range(len(data)))
    vals = " ".join(f"  {b:02X}" for b in data)
    return f"  offs: {offs}\n  vals: {vals}"


def main():
    with ZanacGame.launch() as game:
        msx = game.client

        game.wait_for_title()
        game.start_game()
        time.sleep(3.0)  # wait for enemies to appear

        # Press Z and SHIFT repeatedly to fire weapons
        game.shoot_shot()
        game.shoot_fire()
        time.sleep(0.5)
        game.shoot_shot()
        game.shoot_fire()
        time.sleep(0.5)

        # Single snapshot at entity_dispatch
        msx.cmd("set ::hit_disp 0")
        bp = msx.set_breakpoint(0x445F, "incr ::hit_disp")
        msx.cont()
        # Wait for ~5 dispatch calls
        deadline = time.time() + 5.0
        while time.time() < deadline:
            v = int(msx.cmd("set ::hit_disp"))
            if v >= 5:
                msx.cmd("debug break")
                break
            time.sleep(0.1)
        msx.remove_breakpoint(bp)

        # Read entity slot 0 (player, at 0xE300)
        slot0 = bytes(msx.read_memory(ENTITY_BASE, SLOT_SIZE))
        # Read 0xE100 through 0xE11F (player private state)
        e100 = bytes(msx.read_memory(E100_BASE, 32))
        # Read more entity slots to find active enemy types
        table = bytes(msx.read_memory(ENTITY_BASE, 26 * SLOT_SIZE))

    print("=== Entity slot 0 (player, at 0xE300) ===")
    for row in range(0, 32, 16):
        print(hex32(slot0[row:row+16], row))

    print("\n=== 0xE100-0xE11F (player private state) ===")
    for row in range(0, 32, 16):
        print(hex32(e100[row:row+16], row))

    print("\n=== Active enemy slots ===")
    for i in range(26):
        slot = table[i*32:(i+1)*32]
        t = slot[0] & 0x7F
        if t not in (0, 1, 2, 39, 44):  # show enemy types only
            print(f"\nSlot {i} (type {t} = 0x{t:02X}):")
            for row in range(0, 32, 16):
                print(hex32(slot[row:row+16], row))

    print("\n=== All active slots (type summary) ===")
    for i in range(26):
        slot = table[i*32:(i+1)*32]
        t = slot[0] & 0x7F
        active = (slot[0] >> 7)
        if t > 0:
            print(f"  slot {i:2d}: type {t:3d} (0x{t:02X})  active={active}  "
                  f"Y={slot[1]:3d} X={slot[2]:3d}  "
                  f"+17={slot[0x17]:02X} +18={slot[0x18]:02X}")


if __name__ == "__main__":
    main()
