"""
Verify scripts/no_enemies.ips: launch Zanac with the patch applied,
start the game, run for several seconds, then scan entity slots to confirm
no enemy types are present and the player/shot/fire slots are working.
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from zanackb.openmsx import OpenMsxClient
from zanackb.zanac_game import ZanacGame

ROM  = "source/zanac.rom"
IPS  = "scripts/no_enemies.ips"

# Entity slot layout
SLOT0_ADDR = 0xE300
SLOT_SIZE  = 0x20
NUM_SLOTS  = 26   # slots 0-25

PLAYER_TYPES = {1, 2, 3}       # ship, shot, fire
ENEMY_RANGE  = range(4, 90)    # all other entity types


def scan_slots(msx):
    raw = bytes(msx.read_memory(SLOT0_ADDR, NUM_SLOTS * SLOT_SIZE))
    slots = []
    for i in range(NUM_SLOTS):
        base = i * SLOT_SIZE
        # +0x00 = type_flags; bits 0-6 = entity type, bit 7 = active flag
        type_flags = raw[base + 0]
        etype = type_flags & 0x7F
        slots.append((i, etype, type_flags))
    return slots


def main():
    print(f"Launching openMSX with IPS patch: {IPS}")

    client, proc = OpenMsxClient.connect_subprocess(
        rom=ROM,
        extra_args=("-ips", IPS),
        timeout=20.0,
    )
    game = ZanacGame(client, proc)

    try:
        # Replicate ZanacGame.launch cold-start sequence
        msx = client
        msx.cmd("set ::zanac_cold_start 0")
        bp = msx.set_breakpoint(0x4010, "set ::zanac_cold_start 1")
        msx.power_on()
        msx.poll_flag("zanac_cold_start", interval=0.3, timeout=12.0)
        msx.remove_breakpoint(bp)
        print("Cart INIT reached — ROM active.")

        game.wait_for_title()
        print("Title screen detected.")

        game.start_game()
        print("Game started — waiting 5 s for gameplay...")

        # Make player invincible so we can observe without dying
        time.sleep(0.5)
        msx.write_byte(0xE305, msx.read_byte(0xE305) | 0x80)  # bit7 = invincible
        msx.write_byte(0xE31B, 0xFF)

        # Fire shots and fire weapon, then let level run
        game.shoot_shot()       # hold SHIFT for normal shots
        game.shoot_fire()       # hold Z for fire weapon
        time.sleep(6.0)
        game.release_shot()
        game.release_fire()

        slots = scan_slots(msx)

        # --- Report active slots ---
        print("\nActive entity slots:")
        active_enemies = []
        active_players = []
        for idx, etype, flags in slots:
            if etype == 0:
                continue
            role = "PLAYER" if etype in PLAYER_TYPES else "ENEMY"
            print(f"  slot {idx:2d}: type={etype:3d} flags=0x{flags:02X}  [{role}]")
            if etype in PLAYER_TYPES:
                active_players.append(etype)
            elif etype in ENEMY_RANGE:
                active_enemies.append((idx, etype))

        print()
        if active_enemies:
            print(f"FAIL: {len(active_enemies)} enemy slot(s) still active: {active_enemies}")
        else:
            print("PASS: no enemy entities found in any slot.")

        if active_players:
            print(f"PASS: player-side entities present (types {active_players}).")
        else:
            print("WARN: no player-side entities found — check that game started.")

    finally:
        game.cleanup()
        proc.terminate()
        proc.wait()


if __name__ == "__main__":
    main()
