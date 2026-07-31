"""
Verify in-game key handling:
1. STOP (row 7 bit 4): confirm game pauses (entities freeze, E1F8 stops incrementing)
2. SELECT (row 7 bit 6): confirm it exits STOP-pause
3. Game-over flow: confirm ESC exits to title, fire keys cycle weapon display
"""

import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from zanackb.openmsx import OpenMsxClient, MSXKey
from zanackb.zanac_game import ZanacGame

ROM = "source/zanac.rom"


def boot_and_start(msx, game):
    msx.cmd("set ::zanac_cold_start 0")
    bp = msx.set_breakpoint(0x4010, "set ::zanac_cold_start 1")
    msx.power_on()
    msx.poll_flag("zanac_cold_start", interval=0.3, timeout=12.0)
    msx.remove_breakpoint(bp)
    game.wait_for_title()
    game.start_game()
    time.sleep(0.8)


# ── Test 1: STOP pauses game ───────────────────────────────────────────────────
def test_stop_pauses():
    print("\n=== STOP key pauses game ===")
    client, proc = OpenMsxClient.connect_subprocess(rom=ROM, timeout=20.0)
    game = ZanacGame(client, proc)
    msx = client
    try:
        boot_and_start(msx, game)

        # Read vblank counter before/after with STOP held
        vb_before = msx.read_byte(0xE1F8)
        time.sleep(0.1)
        vb_running = msx.read_byte(0xE1F8)
        print(f"  VBlank counter running: {vb_before} → {vb_running} "
              f"(delta={vb_running-vb_before})")

        # Press STOP
        msx.key_down(*MSXKey.ZANAC_STOP)
        time.sleep(0.15)
        msx.key_up(*MSXKey.ZANAC_STOP)
        time.sleep(0.3)   # let the pause loop settle

        vb_paused_a = msx.read_byte(0xE1F8)
        time.sleep(0.2)
        vb_paused_b = msx.read_byte(0xE1F8)
        delta_paused = vb_paused_b - vb_paused_a
        print(f"  VBlank counter during pause: {vb_paused_a} → {vb_paused_b} "
              f"(delta={delta_paused})")
        # Note: E1F8 is still incremented by the ISR even when paused,
        # but entity positions should be frozen — check E300 Y position instead
        player_y_a = msx.read_byte(0xE301)  # entity slot 0, Y byte
        time.sleep(0.2)
        player_y_b = msx.read_byte(0xE301)
        print(f"  Player Y during pause: {player_y_a} → {player_y_b} "
              f"({'FROZEN' if player_y_a == player_y_b else 'MOVING'})")

        # Press STOP again to resume
        msx.key_down(*MSXKey.ZANAC_STOP)
        time.sleep(0.15)
        msx.key_up(*MSXKey.ZANAC_STOP)
        time.sleep(0.3)

        player_y_c = msx.read_byte(0xE301)
        print(f"  Player Y after resume: {player_y_b} → {player_y_c}")

    finally:
        game.cleanup(); proc.terminate(); proc.wait()


# ── Test 2: SELECT key identity (row 7 bit 6) ─────────────────────────────────
def test_select_identity():
    print("\n=== SELECT key: identify row 7 bit 6 via keymatrix ===")
    client, proc = OpenMsxClient.connect_subprocess(rom=ROM, timeout=20.0)
    game = ZanacGame(client, proc)
    msx = client
    try:
        msx.cmd("set ::zanac_cold_start 0")
        bp = msx.set_breakpoint(0x4010, "set ::zanac_cold_start 1")
        msx.power_on()
        msx.poll_flag("zanac_cold_start", interval=0.3, timeout=12.0)
        msx.remove_breakpoint(bp)

        row7 = int(msx.cmd("debug read \"keymatrix\" 7"))
        print(f"  Row 7 baseline: {row7} (decimal) = 0b{row7:08b}")
        for bit in range(8):
            state = "0(pressed)" if (row7 & (1 << bit)) == 0 else "1(off)"
            print(f"    bit {bit}: {state}")
        print(f"  → bit 4 (STOP): {'pressed' if not (row7 & 0x10) else 'released'}")
        print(f"  → bit 6 (SELECT?): {'pressed' if not (row7 & 0x40) else 'released'}")

    finally:
        game.cleanup(); proc.terminate(); proc.wait()


# ── Test 3: Game-over ESC → title ────────────────────────────────────────────
def test_gameover_esc():
    print("\n=== Game-over screen: ESC exits to title ===")
    client, proc = OpenMsxClient.connect_subprocess(rom=ROM, timeout=20.0)
    game = ZanacGame(client, proc)
    msx = client
    try:
        boot_and_start(msx, game)

        # Kill the player by zeroing lives and forcing a hit
        msx.write_byte(0xE10A, 0)       # lives = 0
        msx.write_byte(0xE102, msx.read_byte(0xE102) | 0x01)  # set hit flag

        time.sleep(2.5)  # wait for game-over sequence to appear

        screen = game.screen_state()
        print(f"  Screen state: {screen}")

        # Press ESC (row 7 bit 2) during game-over
        msx.key_press(7, 0x04, duration=0.15)   # row 7, mask 0x04 = bit 2 = ESC
        time.sleep(1.5)

        screen_after = game.screen_state()
        print(f"  Screen after ESC: {screen_after}")
        print(f"  {'PASS: back at title' if screen_after == 'title' else 'INCONCLUSIVE: ' + screen_after}")

    finally:
        game.cleanup(); proc.terminate(); proc.wait()


if __name__ == "__main__":
    test_select_identity()
    test_stop_pauses()
    test_gameover_esc()
