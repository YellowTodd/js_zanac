"""Sprint 0024 — Animation table confirmation.

1. Boot openMSX, wait for cold_start so ROM page 2 is mapped.
2. Read the type-35 animation table from ROM (0x84D1).
3. Play briefly, scan entity slots for any with +0x0C bit2 set.
4. For each unique table address, read and decode the animation frames.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from zanackb.zanac_game import ZanacGame

ENTITY_BASE = 0xE300
SLOT_SIZE   = 32
NUM_SLOTS   = 26

# Sprite name table (pattern index → name) from zanac-sprite-names.md
SPRITE_NAMES = {
    0: "empty", 1: "power_chip", 2: "comet", 3: "target", 4: "snowflake",
    5: "small_star", 6: "light_bar", 7: "lead", 8: "med_circle", 9: "lg_circle",
    10: "shot_single", 11: "shot_double", 12: "shot_triple",
    13: "super_hard_bolt", 14: "player_ship", 15: "player_compl",
    16: "plane", 17: "plane_compl",
    18: "loga_A", 19: "loga_B", 20: "loga_complA", 21: "loga_complB",
    22: "duster", 23: "duster_compl",
    24: "teruzo", 25: "teruzo_compl",
    26: "sig_triple", 27: "sig_double", 28: "sig_single",
    29: "luster_A", 30: "luster_B", 31: "luster_complA", 32: "luster_complB",
    33: "veybar_A", 34: "veybar_B", 35: "veybar_C", 36: "veybar_D", 37: "veybar_E",
    38: "veybar_complA", 39: "veybar_complB", 40: "veybar_complC",
    41: "veybar_complD", 42: "veybar_complE",
    43: "spinner_A", 44: "spinner_B", 45: "spinner_C", 46: "spinner_D",
    47: "spinner_complA", 48: "spinner_complB", 49: "spinner_complC", 50: "spinner_complD",
    51: "stealth", 52: "stealth_compl",
    53: "box", 54: "box_compl",
    55: "umber_A", 56: "umber_B", 57: "umber_complA", 58: "umber_complB",
    59: "degid_left", 60: "degid_right", 61: "degid_complete",
    62: "sart", 63: "sart_compl",
}


def sat_name_to_pattern(sat_name: int) -> int:
    return sat_name >> 2


def decode_table(data: bytes, n_frames: int) -> list[tuple[int, int, str]]:
    """Decode n_frames × (sat_name, sat_color) from bytes."""
    rows = []
    for i in range(n_frames):
        if i * 2 + 1 >= len(data):
            break
        sat_name  = data[i * 2]
        sat_color = data[i * 2 + 1]
        pat = sat_name_to_pattern(sat_name)
        name = SPRITE_NAMES.get(pat, f"pat{pat}")
        rows.append((sat_name, sat_color, name))
    return rows


def print_table(addr: int, rows: list, label: str = ""):
    header = f"Table at 0x{addr:04X}" + (f"  [{label}]" if label else "")
    print(header)
    for i, (sn, sc, name) in enumerate(rows):
        pat = sat_name_to_pattern(sn)
        print(f"  frame {i}: sat_name=0x{sn:02X} pat={pat:2d} ({name:20s})  sat_color=0x{sc:02X}")


def main():
    print("Launching openMSX...")
    with ZanacGame.launch() as game:
        msx = game.client

        # --- Phase 1: read type-35 table directly from ROM (no gameplay needed) ---
        print("\n=== Phase 1: ROM animation table reads ===\n")

        # Type 35 confirmed: table=0x84D1, frames=6
        type35_data = msx.read_memory(0x84D1, 6 * 2)
        rows35 = decode_table(type35_data, 6)
        print_table(0x84D1, rows35, "type 35 (confirmed, +0x10=6)")

        # Read a broader window around 0x84D1 in case table is longer
        window = msx.read_memory(0x84A0, 0x60)
        print(f"\nROM window 0x84A0–0x84FF (hex):")
        for i in range(0, len(window), 16):
            chunk = window[i:i+16]
            addr  = 0x84A0 + i
            print(f"  {addr:04X}: {' '.join(f'{b:02X}' for b in chunk)}")

        # --- Phase 2: play briefly to catch other bit2 entities ---
        print("\n=== Phase 2: gameplay scan for bit2 entity types ===\n")

        print("Waiting for title...")
        game.wait_for_title()
        print("Starting game...")
        game.start_game()
        time.sleep(3.0)   # let enemies appear

        game.steer(up=True)   # move ship to attract enemies

        # Capture 10 snapshots at entity_dispatch
        msx.cmd("set ::disp_n 0")
        bp = msx.set_breakpoint(
            0x445F,
            "incr ::disp_n; if {$::disp_n % 5 == 0} {debug break}"
        )

        # table_addr → (type, max_frames, rows)
        found: dict[int, tuple[int, int, list]] = {}

        for sample in range(15):
            msx.cont()
            time.sleep(0.35)
            raw = msx.read_memory(ENTITY_BASE, NUM_SLOTS * SLOT_SIZE)
            for i in range(NUM_SLOTS):
                slot = raw[i * SLOT_SIZE:(i + 1) * SLOT_SIZE]
                typ  = slot[0] & 0x7F
                if typ == 0:
                    continue
                oC = slot[0x0C]
                if not (oC & 0x04):   # bit2 must be set
                    continue
                max_frames  = slot[0x10]
                table_lo    = slot[0x11]
                table_hi    = slot[0x12]
                table_addr  = (table_hi << 8) | table_lo
                if table_addr == 0 or max_frames == 0:
                    continue
                if table_addr not in found:
                    tbl_data = msx.read_memory(table_addr, max_frames * 2)
                    rows     = decode_table(tbl_data, max_frames)
                    found[table_addr] = (typ, max_frames, rows)
                    print(f"  sample {sample}: slot {i} type {typ} → table 0x{table_addr:04X}"
                          f"  frames={max_frames}  tick_rate={slot[0x0E]}"
                          f"  +0x0C=0x{oC:02X}")

        msx.remove_breakpoint(bp)

        print("\n=== Animation tables found ===\n")
        for addr, (typ, nf, rows) in sorted(found.items()):
            print_table(addr, rows, f"type {typ} (first seen), {nf} frames")
            print()


if __name__ == "__main__":
    main()
