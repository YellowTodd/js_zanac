"""Sprint 0026 — Player-tracking entity types 31 and 33.

Phase 1: ROM decode of handler at 0x7F84.
Phase 2: Live injection of type 31 into a free slot, 30-frame observation.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from zanackb.zanac_game import ZanacGame

ENTITY_BASE = 0xE300
SLOT_SIZE   = 32
SLOT5_BASE  = 0xE3A0   # slot 5


def decode_slot5(msx) -> str:
    s = bytes(msx.read_memory(SLOT5_BASE, SLOT_SIZE))
    typ = s[0] & 0x7F
    return (f"type={typ} Y={s[1]:3d} X={s[2]:3d} sat={s[3]:02X} col={s[4]:02X}"
            f" +0C={s[0x0C]:02X} +0D={s[0x0D]:02X} +09={s[0x09]:02X}"
            f" +13={s[0x13]:02X} +15={s[0x15]:02X} +17={s[0x17]:02X}")


def main():
    print("Launching openMSX...")
    with ZanacGame.launch() as game:
        msx = game.client

        # ── Phase 1: static ROM decode ────────────────────────────────────────
        print("\n=== Phase 1: ROM at 0x7F84-0x7FFF ===\n")
        data = bytes(msx.read_memory(0x7F84, 0x7C))
        for i in range(0, len(data), 16):
            chunk = data[i:i+16]
            print(f"  {0x7F84+i:04X}: {' '.join(f'{b:02X}' for b in chunk)}")

        # Also read the code that sprint 0021 found (around lines 3262-3316)
        # Approximate address: 0x73A0-0x7400 range
        print("\nROM 0x73A0-0x7430:")
        data2 = bytes(msx.read_memory(0x73A0, 0x90))
        for i in range(0, len(data2), 16):
            chunk = data2[i:i+16]
            print(f"  {0x73A0+i:04X}: {' '.join(f'{b:02X}' for b in chunk)}")

        # ── Phase 2: gameplay injection ───────────────────────────────────────
        print("\n=== Phase 2: Inject type-31, observe homing ===\n")

        print("Waiting for title...")
        game.wait_for_title()
        game.start_game()
        time.sleep(1.5)

        player_y = msx.read_byte(0xE301)
        print(f"Player Y = {player_y}")

        # Inject type-31 into slot 5 with active flag set
        msx.write_byte(SLOT5_BASE + 0x00, 0x9F)  # type=31 (0x1F), bit7=active(1) = 0x9F
        msx.write_byte(SLOT5_BASE + 0x01, 0x20)  # Y = 32
        msx.write_byte(SLOT5_BASE + 0x02, 0x60)  # X = 96
        msx.write_byte(SLOT5_BASE + 0x03, 0x1C)  # sat_name = lead
        msx.write_byte(SLOT5_BASE + 0x04, 0x8F)  # color = white

        print("Injected type-31 at slot 5. Observing 30 frames...")

        # Watch over 30 dispatch breaks
        msx.cmd("set ::dn 0")
        bp = msx.set_breakpoint(0x445F,
            "incr ::dn; if {$::dn % 3 == 0} {debug break}")

        for sample in range(10):
            msx.cont()
            time.sleep(0.15)
            py = msx.read_byte(0xE301)
            print(f"  sample {sample:2d} playerY={py:3d}  slot5: {decode_slot5(msx)}")

        msx.remove_breakpoint(bp)

        # Also check what entity_update bit3 fields look like for type-31
        s5 = bytes(msx.read_memory(SLOT5_BASE, SLOT_SIZE))
        print("\nFull slot 5 after 30 frames:")
        for row in range(0, 32, 8):
            chunk = s5[row:row+8]
            print(f"  +{row:02X}: {' '.join(f'{b:02X}' for b in chunk)}")


if __name__ == "__main__":
    main()
