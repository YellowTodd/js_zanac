"""Sprint 0023 — Fire weapon system: types 0-7 entity mapping.

Phase 1: Inject fire_type 0-7, press Z, capture entity slots.
Phase 2: Read ROM at type-3 handler (0x7253) and sub_7548 to decode statically.
Phase 3: Play one game cycle, watch 0xE14B and slot 4 changes.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from zanackb.openmsx import MSXKey
from zanackb.zanac_game import ZanacGame

ENTITY_BASE = 0xE300
SLOT_SIZE   = 32
NUM_SLOTS   = 26

# Known fire_type address
ADDR_FIRE_TYPE = 0xE14B
ADDR_E10C      = 0xE10C   # fire weapon indicator in player handler
SLOT4_BASE     = 0xE380   # slot 4 (fire weapon slot)


def read_slots(msx) -> list[tuple[int, bytes]]:
    raw = msx.read_memory(ENTITY_BASE, NUM_SLOTS * SLOT_SIZE)
    return [(raw[i*SLOT_SIZE] & 0x7F, raw[i*SLOT_SIZE:(i+1)*SLOT_SIZE])
            for i in range(NUM_SLOTS)]


def dump_slot(idx: int, typ: int, slot: bytes):
    y, x = slot[1], slot[2]
    sat, col = slot[3], slot[4]
    oC = slot[0x0C]
    o1a = slot[0x1A]
    print(f"  slot {idx}: type {typ:3d} (0x{typ:02X})  Y={y:3d} X={x:3d}  "
          f"sat={sat:02X} col={col:02X}  +0C={oC:02X}  +1A={o1a:02X}  "
          f"+1B={slot[0x1B]:02X}{slot[0x1C]:02X}")


def main():
    print("Launching openMSX...")
    with ZanacGame.launch() as game:
        msx = game.client

        # ── Phase 2 (fast): static ROM reads ─────────────────────────────────
        print("\n=== Phase 2: ROM reads (before gameplay) ===\n")

        # Type-3 handler at 0x7253: read 80 bytes
        t3_data = bytes(msx.read_memory(0x7253, 80))
        print("Type-3 handler ROM 0x7253-0x72A2:")
        for i in range(0, 80, 16):
            chunk = t3_data[i:i+16]
            print(f"  {0x7253+i:04X}: {' '.join(f'{b:02X}' for b in chunk)}")

        # sub_7548 — fire weapon upgrader
        t7548 = bytes(msx.read_memory(0x7548, 48))
        print("\nsub_7548 ROM 0x7548-0x7577:")
        for i in range(0, 48, 16):
            chunk = t7548[i:i+16]
            print(f"  {0x7548+i:04X}: {' '.join(f'{b:02X}' for b in chunk)}")

        # sub_5c2e — called with fire_type in A
        sc2e = bytes(msx.read_memory(0x5C2E, 32))
        print("\nsub_5C2E ROM 0x5C2E-0x5C4D:")
        for i in range(0, 32, 16):
            chunk = sc2e[i:i+16]
            print(f"  {0x5C2E+i:04X}: {' '.join(f'{b:02X}' for b in chunk)}")

        # ── Phase 1: gameplay fire injection ─────────────────────────────────
        print("\n=== Phase 1: Fire injection for types 0-7 ===\n")

        print("Waiting for title...")
        game.wait_for_title()
        game.start_game()
        time.sleep(1.5)

        results: dict[int, list[int]] = {}

        for fire_type in range(8):
            # First clear slot 4 manually (wait for any active fire to expire)
            time.sleep(0.25)

            # Set fire_type
            msx.write_byte(ADDR_FIRE_TYPE, fire_type)
            msx.write_byte(ADDR_E10C, fire_type)   # also player's internal ref

            # Press Z (fire weapon)
            msx.key_press(*MSXKey.ZANAC_FIRE, duration=0.12)
            time.sleep(0.08)

            # Snapshot entity slots 0-4
            raw = bytes(msx.read_memory(ENTITY_BASE, 5 * SLOT_SIZE))
            slot_types = [raw[i*SLOT_SIZE] & 0x7F for i in range(5)]
            results[fire_type] = slot_types

            # Read slot 4 in detail
            s4 = raw[4*SLOT_SIZE:5*SLOT_SIZE]
            t4 = s4[0] & 0x7F
            active = (s4[0] >> 7)
            e14b = msx.read_byte(ADDR_FIRE_TYPE)
            e10c = msx.read_byte(ADDR_E10C)
            print(f"fire_type={fire_type}:  0xE14B={e14b}  0xE10C={e10c}  "
                  f"slot4=type{t4}(active={active})  "
                  f"all={slot_types}")
            if t4 != 0:
                dump_slot(4, t4, s4)

        # ── Extended run: watch slot 4 evolve over time ─────────────────────
        print("\n=== Extended: watch slot 4 for fire_type=1 over 1s ===\n")
        msx.write_byte(ADDR_FIRE_TYPE, 1)
        msx.write_byte(ADDR_E10C, 1)
        msx.key_press(*MSXKey.ZANAC_FIRE, duration=0.12)
        time.sleep(0.05)

        for _ in range(8):
            time.sleep(0.12)
            s4 = bytes(msx.read_memory(SLOT4_BASE, SLOT_SIZE))
            t4 = s4[0] & 0x7F
            y, x = s4[1], s4[2]
            sat, col = s4[3], s4[4]
            print(f"  slot4: type={t4} Y={y} X={x} sat={sat:02X} col={col:02X} "
                  f"+0C={s4[0x0C]:02X} +17={s4[0x17]:02X} +1A={s4[0x1A]:02X}")

        # ── Summary ───────────────────────────────────────────────────────────
        print("\n=== Summary: fire_type → entity types (slots 0-4) ===")
        for ft, types in results.items():
            print(f"  fire_type {ft}: {types}")

        # ── Final game state ─────────────────────────────────────────────────
        print(f"\n0xE14B={msx.read_byte(0xE14B)}  0xE10C={msx.read_byte(0xE10C)}")
        print(f"0xE10B (shot_level)={msx.read_byte(0xE10B)}")


if __name__ == "__main__":
    main()
