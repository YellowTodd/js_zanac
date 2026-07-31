"""
Verify title-screen key handling discoveries:
1. SHIFT (row 6 bit 0) can start the game without SPACE
2. Z (row 5 bit 7) can start the game without SPACE
3. Row 7 bit 2 held at title_screen_init → stage 0 start (0xA65C vs 0xA751)

Strategy for row7bit2 test: break inside check_start_key (0x43D2) right at
the BIT instruction (0x43D7), then force A bit2=0 (= key pressed) via reg write.
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from zanackb.openmsx import OpenMsxClient, MSXKey
from zanackb.zanac_game import ZanacGame

ROM = "source/zanac.rom"

# check_start_key: 0x43D2=LD A,7 / 0x43D4=CALL 0x0141 / 0x43D7=BIT 0x2,A / 0x43D9=RET
ADDR_BIT_INSTR  = 0x43D7    # BIT 0x2, A  — intercept here, force A bit2=0

# title_screen_init uses HL (from table) to call sub_9405, which sets E704 = HL+2
# Then sub_9ae4/946e advance E704 by a fixed amount.  We'll compare the two final values.
NORMAL_E704_OFFSET  = 0xA753  # 0xA751 + 2
SECRET_E704_OFFSET  = 0xA65E  # 0xA65C + 2


def boot_to_breakpoint(msx, game):
    """Power on and wait for cart INIT."""
    msx.cmd("set ::zanac_cold_start 0")
    bp = msx.set_breakpoint(0x4010, "set ::zanac_cold_start 1")
    msx.power_on()
    msx.poll_flag("zanac_cold_start", interval=0.3, timeout=12.0)
    msx.remove_breakpoint(bp)


def e704_val(msx):
    lo = msx.read_byte(0xE704)
    hi = msx.read_byte(0xE705)
    return lo | (hi << 8)


# ── Test 1: SHIFT starts game ──────────────────────────────────────────────────

def test_fire_key(key_name, key_down, key_up):
    print(f"\n=== {key_name} starts game ===")
    client, proc = OpenMsxClient.connect_subprocess(rom=ROM, timeout=20.0)
    game = ZanacGame(client, proc)
    msx = client
    try:
        boot_to_breakpoint(msx, game)
        game.wait_for_title()

        # Break at title_screen_init to read E100 right after key press
        msx.cmd("set ::reached 0")
        bp = msx.set_breakpoint(0x41DB, "set ::reached 1; debug break")
        msx.cont()

        key_down(msx)
        time.sleep(0.4)
        key_up(msx)
        time.sleep(0.2)

        msx.remove_breakpoint(bp)

        if msx.cmd("set ::reached").strip() == "1":
            e100 = msx.read_byte(0xE100)
            print(f"  Hit title_screen_init. E100=0x{e100:02X} "
                  f"(bits 4,5 = {(e100>>4)&3})")
            print(f"  {'PASS: at least one fire bit is clear' if (e100 & 0x30) != 0x30 else 'FAIL: fire bits still set'}")
            msx.cont()
            time.sleep(1.0)
            e701 = msx.read_byte(0xE701)
            e704 = e704_val(msx)
            print(f"  E701=0x{e701:02X} E704=0x{e704:04X}")
        else:
            print(f"  FAIL: never reached title_screen_init")

    finally:
        game.cleanup()
        proc.terminate()
        proc.wait()


# ── Test 2: row 7 bit 2 → stage 0 start ───────────────────────────────────────

def test_row7bit2_secret():
    print("\n=== row-7-bit-2 secret: forced A bit2=0 at BIT instr ===")
    client, proc = OpenMsxClient.connect_subprocess(rom=ROM, timeout=20.0)
    game = ZanacGame(client, proc)
    msx = client
    try:
        boot_to_breakpoint(msx, game)
        game.wait_for_title()

        # Set breakpoint BEFORE pressing SPACE so we don't miss it
        msx.cmd("set ::at_bit 0")
        bp = msx.set_breakpoint(ADDR_BIT_INSTR,
                                "set ::at_bit 1; debug break")

        # Now press SPACE to trigger title_screen_init path
        game.fire_shot(duration=0.15)
        time.sleep(1.0)   # wait for title_intro_seq to detect the press

        if msx.cmd("set ::at_bit").strip() != "1":
            print("  FAIL: never reached BIT instruction in check_start_key")
            msx.remove_breakpoint(bp)
            return

        # CPU is paused at 0x43D7 (BIT 0x2, A).
        # Force A bit 2 = 0  (simulate row7bit2 key pressed)
        a_val = int(msx.cmd("reg a"))
        a_patched = a_val & ~0x04
        msx.cmd(f"reg a {a_patched}")
        print(f"  Patched A: 0x{a_val:02X} -> 0x{a_patched:02X} (bit2 cleared)")

        msx.remove_breakpoint(bp)
        msx.cont()
        time.sleep(1.5)

        e701 = msx.read_byte(0xE701)
        e704 = e704_val(msx)
        print(f"  E701=0x{e701:02X}  E704=0x{e704:04X}")

        if e701 == 0:
            print("  PASS: E701=0 — stage 0 secret confirmed!")
        else:
            print(f"  FAIL: E701={e701} (expected 0)")

        # Work out which start address was used
        # sub_9ae4 and sub_946e advance E704 by 8 bytes (observed), so subtract back
        # Actually just check which region E704 is in
        if 0xA65E <= e704 < 0xA800:
            print(f"  PASS: E704 in secret-start region (0xA65C+)")
        elif 0xA753 <= e704 < 0xA900:
            print(f"  FAIL: E704 in normal-start region (0xA751+)")
        else:
            print(f"  UNCLEAR: E704=0x{e704:04X}")

    finally:
        game.cleanup()
        proc.terminate()
        proc.wait()


# ── Test 3: normal SPACE (baseline) ───────────────────────────────────────────

def test_normal_baseline():
    print("\n=== Normal SPACE baseline ===")
    client, proc = OpenMsxClient.connect_subprocess(rom=ROM, timeout=20.0)
    game = ZanacGame(client, proc)
    msx = client
    try:
        boot_to_breakpoint(msx, game)
        game.wait_for_title()
        game.fire_shot(duration=0.15)

        # Let game init fully run
        time.sleep(2.0)
        e701 = msx.read_byte(0xE701)
        e704 = e704_val(msx)
        print(f"  E701=0x{e701:02X}  E704=0x{e704:04X}")
        print(f"  {'PASS: normal start' if e701 == 1 else 'FAIL: unexpected E701'}")
    finally:
        game.cleanup()
        proc.terminate()
        proc.wait()


if __name__ == "__main__":
    test_normal_baseline()
    test_fire_key(
        "SHIFT only",
        lambda msx: msx.key_down(*MSXKey.ZANAC_SHOT),
        lambda msx: msx.key_up(*MSXKey.ZANAC_SHOT),
    )
    test_fire_key(
        "Z only",
        lambda msx: msx.key_down(*MSXKey.ZANAC_FIRE),
        lambda msx: msx.key_up(*MSXKey.ZANAC_FIRE),
    )
    test_row7bit2_secret()
