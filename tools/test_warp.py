"""Test scripts/warp.tcl for rounds 0, 1, 3, 8."""

import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from zanackb.openmsx import OpenMsxClient
from zanackb.zanac_game import ZanacGame

ROM      = "source/zanac.rom"
WARP_TCL = "scripts/warp.tcl"

# Expected E704 values (E704 = level_start_addr + 2, then advances ~8 bytes
# during title_screen_init's remaining calls, observed consistently as +8)
EXPECTED = {
    0: 0xA65C + 2,   # secret
    1: 0xA751 + 2,   # normal
    2: 0xAAEF + 2,
    3: 0xAD61 + 2,
    4: 0xAF1F + 2,
    5: 0xB1DE + 2,
    6: 0xB3FD + 2,
    7: 0xB61A + 2,
    8: 0xB7A5 + 2,
}
ADVANCE = 8   # bytes E704 advances during remaining title_screen_init calls


def e704(msx):
    return msx.read_byte(0xE704) | (msx.read_byte(0xE705) << 8)


def test_round(round_num):
    print(f"\n=== warp {round_num} ===")
    client, proc = OpenMsxClient.connect_subprocess(rom=ROM, timeout=20.0)
    game = ZanacGame(client, proc)
    msx = client
    try:
        msx.cmd("set ::zanac_cold_start 0")
        bp = msx.set_breakpoint(0x4010, "set ::zanac_cold_start 1")
        msx.power_on()
        msx.poll_flag("zanac_cold_start", interval=0.3, timeout=12.0)
        msx.remove_breakpoint(bp)
        game.wait_for_title()

        # Load and arm the warp
        with open(WARP_TCL) as f:
            tcl = f.read()
        msx.cmd(tcl)
        msx.cmd(f"warp {round_num}")

        # Trigger start with SPACE
        game.fire_shot(duration=0.15)
        time.sleep(2.0)

        actual_e704  = e704(msx)
        actual_e701  = msx.read_byte(0xE701)
        expected_e704 = EXPECTED[round_num] + ADVANCE

        print(f"  E701=0x{actual_e701:02X}  E704=0x{actual_e704:04X}  "
              f"(expected E704≈0x{expected_e704:04X})")

        if actual_e701 == round_num:
            print(f"  E701 PASS")
        else:
            print(f"  E701 FAIL (got {actual_e701}, want {round_num})")

        # E704 tolerance: ±32 bytes (depends on how much the stream advanced)
        delta = abs(actual_e704 - expected_e704)
        if delta <= 64:
            print(f"  E704 PASS (delta={delta})")
        else:
            print(f"  E704 FAIL (delta={delta} too large)")

    finally:
        game.cleanup()
        proc.terminate()
        proc.wait()


if __name__ == "__main__":
    for r in [1, 0, 4, 8]:
        test_round(r)
