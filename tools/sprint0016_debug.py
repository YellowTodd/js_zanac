#!/usr/bin/env python3
"""Sprint 0016 — Player bullet system debug script.

Goal: map each weapon level (0–7) to its SAT_NAME pattern byte and Y velocity.

Key addresses:
  0xE10B  weapon number (current weapon level 0–7)
  0xE10D  ??? (written by weapon_load_params)
  0xE10E  bullet Y velocity (negative, CPL'd before storing to IX+0x09)
  0xE10F  bullet SAT_NAME pattern byte (stored to IX+0x03)
  0x778F  weapon param table: 8+ entries × 3 bytes [vy, byte1, sat_name]
  0x445F  entity_dispatch (breakpoint to capture entity slots)
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from zanackb.openmsx import OpenMsxClient, OpenMsxError

SPRITE_NAMES = {
    0x00: "invis",
    0x04: "pat1",
    0x08: "pat2",
    0x0C: "pat3",
    0x10: "pat4",
    0x14: "pat5",
    0x18: "light_bar",
    0x1C: "lead",
    0x20: "med_circle",
    0x24: "large_circle",
    0x28: "shot_single",
    0x2C: "shot_double",
    0x30: "shot_triple",
    0x34: "pat13",
    0x38: "player_ship",
    0x3C: "pat15",
    0x40: "plane",
    0x44: "plane_shadow",
    0x48: "pat18",
    0x4C: "pat19",
    0x50: "pat20",
    0x54: "pat21",
    0x58: "duster",
    0x5C: "duster_sh",
    0x60: "teruzo",
    0x64: "teruzo_sh",
    0x68: "pat26",
    0x6C: "pat27",
    0x70: "sig_single",
    0x74: "luster_A",
    0x78: "pat30",
    0x7C: "pat31",
    0x80: "pat32",
    0x84: "veybar_A",
    0x88: "pat34",
    0x8C: "pat35",
    0x90: "pat36",
    0x94: "pat37",
    0x98: "veybar_shA",
    0x9C: "pat39",
    0xA0: "pat40",
    0xA4: "pat41",
    0xA8: "pat42",
    0xAC: "pat43",
    0xB0: "pat44",
    0xB4: "pat45",
    0xB8: "pat46",
    0xBC: "pat47",
    0xC0: "pat48",
    0xC4: "pat49",
    0xC8: "pat50",
    0xCC: "pat51",
    0xD0: "pat52",
    0xD4: "box",
    0xD8: "pat54",
    0xDC: "umber_A",
    0xE0: "pat56",
    0xE4: "umber_shA",
}


def sprite_name(sat: int) -> str:
    pat_idx = sat >> 2
    name = SPRITE_NAMES.get(sat, f"pat{pat_idx}")
    return f"{name} (pat{pat_idx}, SAT=0x{sat:02X})"


def read_weapon_table(client: OpenMsxClient) -> None:
    """Read and decode the weapon param table at 0x778F (8 entries × 3 bytes)."""
    print("=== Weapon param table at 0x778F ===")
    client.cmd("debug break")
    time.sleep(0.1)

    # Read 8 weapons × 3 bytes = 24 bytes
    data = client.read_memory(0x778F, 24)

    print(f"Raw bytes: {data.hex()}")
    print()
    print(f"{'Wpn':>4}  {'vy_raw':>8}  {'byte1':>7}  {'SAT_NAME':>10}  sprite")
    print("-" * 70)
    for w in range(8):
        vy_raw = data[w * 3 + 0]
        byte1  = data[w * 3 + 1]
        sat    = data[w * 3 + 2]
        # vy is CPL'd before storing to IX+0x09; restore original meaning:
        # CPL(vy_raw) = ~vy_raw; the entity moves up so vy = -(~vy_raw+1) = vy_raw
        vy_neg = (~vy_raw) & 0xFF  # what gets stored after CPL
        print(f"  {w:2d}    0x{vy_raw:02X} ({vy_raw:3d})  0x{byte1:02X}     0x{sat:02X}       {sprite_name(sat)}")

    client.cont()


def read_live_weapon_state(client: OpenMsxClient) -> None:
    """Read current weapon state variables from RAM."""
    print("=== Live weapon state ===")
    client.cmd("debug break")
    time.sleep(0.1)

    e10a = client.read_memory(0xE10A, 10)
    print(f"0xE10A-0xE113: {e10a.hex()}")
    print(f"  0xE10B = 0x{e10a[1]:02X}  weapon_num")
    print(f"  0xE10C = 0x{e10a[2]:02X}  fire_power?")
    print(f"  0xE10D = 0x{e10a[3]:02X}  (byte1 from table)")
    print(f"  0xE10E = 0x{e10a[4]:02X}  bullet vy raw")
    print(f"  0xE10F = 0x{e10a[5]:02X}  bullet SAT_NAME → {sprite_name(e10a[5])}")
    print(f"  0xE110 = 0x{e10a[6]:02X}")
    print(f"  0xE111 = 0x{e10a[7]:02X}")

    e14b = client.read_memory(0xE14B, 4)
    print(f"0xE14B = 0x{e14b[0]:02X}  fire_num / active shots")
    print(f"0xE14C = 0x{e14b[1]:02X}  fire_counter")

    client.cont()


def capture_bullet_slots(client: OpenMsxClient, n_breaks: int = 5) -> None:
    """Break at entity_dispatch n times, show type-2 bullet slots."""
    print(f"=== Bullet slot capture ({n_breaks} frames) ===")
    bp = client.set_breakpoint(0x445F, "debug break")
    print(f"Breakpoint at entity_dispatch (0x445F): {bp}")

    for frame in range(n_breaks):
        client.cont()
        time.sleep(0.8)
        pc = client.cmd("reg PC")

        raw = client.read_memory(0xE300, 26 * 32)
        # Also grab weapon state
        wpn_state = client.read_memory(0xE10B, 5)  # E10B..E10F
        weapon_num = wpn_state[0]
        sat_live   = wpn_state[4]

        bullet_slots = []
        for i in range(26):
            slot = raw[i * 32:(i + 1) * 32]
            if slot[0] == 2:  # type 2 = player bullet
                pat = slot[3]
                col = slot[4]
                vy  = slot[9]
                bullet_slots.append((i, pat, col, vy))

        print(f"\nFrame {frame+1}: PC=0x{int(pc):04X}  weapon={weapon_num}  E10F=0x{sat_live:02X} ({sprite_name(sat_live)})")
        if bullet_slots:
            for (si, pat, col, vy) in bullet_slots:
                print(f"  slot {si:2d}: SAT=0x{pat:02X} → {sprite_name(pat)}  color=0x{col:02X}  vy=0x{vy:02X}")
        else:
            print("  (no active type-2 bullet slots)")

    client.remove_breakpoint(bp)
    client.cont()


def inject_weapon_change(client: OpenMsxClient, weapon: int) -> None:
    """Force weapon number to 'weapon' (0–7) by writing 0xE10B and reloading params.

    Also calls the param-reload routine to update E10E/E10F.
    """
    print(f"=== Injecting weapon {weapon} ===")
    # Write weapon number to 0xE10B
    client.cmd("debug break")
    time.sleep(0.1)
    client.cmd(f"debug write memory 0xe10b {weapon}")
    # Re-read live state so we can confirm
    e10b = client.read_memory(0xE10B, 1)[0]
    print(f"  0xE10B now = 0x{e10b:02X}")
    client.cont()


def scan_all_weapons(client: OpenMsxClient) -> None:
    """Read table then confirm with watchpoint on 0xE10F writes."""
    print("=== Full weapon scan from table ===")
    read_weapon_table(client)
    print()
    read_live_weapon_state(client)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Sprint 0016 — player bullet debug")
    p.add_argument("cmd", choices=["table", "state", "capture", "scan", "inject"],
                   help="table: dump weapon table; state: live weapon vars; "
                        "capture: break at dispatch and show bullets; "
                        "scan: table+state; inject: force a weapon")
    p.add_argument("--frames", type=int, default=5, help="frames for capture")
    p.add_argument("--weapon", type=int, default=0, help="weapon number for inject")
    args = p.parse_args()

    client = OpenMsxClient.autoconnect()
    print("Connected to openMSX.")

    try:
        if args.cmd == "table":
            read_weapon_table(client)
        elif args.cmd == "state":
            read_live_weapon_state(client)
        elif args.cmd == "capture":
            capture_bullet_slots(client, args.frames)
        elif args.cmd == "scan":
            scan_all_weapons(client)
        elif args.cmd == "inject":
            inject_weapon_change(client, args.weapon)
    finally:
        client.close()
