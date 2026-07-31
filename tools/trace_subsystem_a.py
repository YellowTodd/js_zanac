#!/usr/bin/env python3
"""Live-trace Subsystem A boot routines in openMSX to confirm static analysis.

Catches three boot routines by setting debug-break breakpoints and re-running
the boot via `reset`:
  - map_page2 post-detect_slot (0x4E4A) — reg A = resolved cartridge slot id
    (break here, not detect_slot's 0x4E7A RET, which is only reached for an
    expanded slot; a non-expanded slot exits early via RET P at 0x4E67)
  - init_vdp_regs RET (0x42CE) — read VDP registers 0-7, compare vdp_init_table
  - init_screen_mode RET (0x42B9) — name table filled with 0x20, SAT[0].Y=0xD0,
    sprite_count=0, entity table zeroed
"""
import sys, time
sys.path.insert(0, "tools")
from zanackb.zanac_game import ZanacGame

EXPECT_VDP = bytes([0x02, 0x82, 0x0E, 0xFF, 0x03, 0x77, 0x03, 0x01])

def main():
    with ZanacGame.launch("source/zanac.rom") as game:
        msx = game.client
        for f in ("ds", "vr", "sm"):
            msx.cmd(f"set ::a_{f} 0")
        bp_ds = msx.set_breakpoint(0x4E4A, "set ::a_ds 1; debug break")
        bp_vr = msx.set_breakpoint(0x42CE, "set ::a_vr 1; debug break")
        bp_sm = msx.set_breakpoint(0x42B9, "set ::a_sm 1; debug break")

        # Re-run the boot sequence from scratch.
        msx.reset()

        # 1) map_page2 / detect_slot result ------------------------------------
        ok = msx.poll_flag("a_ds", interval=0.2, timeout=15.0)
        pc = int(msx.cmd("reg pc"))
        a = int(msx.cmd("reg a"))
        e = int(msx.cmd("reg e"))
        print(f"[map_page2] hit={ok} pc=0x{pc:04X} -> A=0x{a:02X} (slot id), "
              f"E=0x{e:02X} (page) — ENASLT maps this slot at page 2")
        msx.cont()

        # 2) init_vdp_regs RET --------------------------------------------------
        ok = msx.poll_flag("a_vr", interval=0.2, timeout=15.0)
        regs = msx.read_debuggable("VDP regs", 0, 8)
        print(f"[init_vdp_regs] hit={ok} pc=0x{int(msx.cmd('reg pc')):04X}")
        print(f"    VDP R0-7 = {regs.hex()}")
        print(f"    expected = {EXPECT_VDP.hex()}  match={regs == EXPECT_VDP}")
        msx.cont()

        # 3) init_screen_mode RET ----------------------------------------------
        ok = msx.poll_flag("a_sm", interval=0.2, timeout=15.0)
        name = msx.read_debuggable("VRAM", 0x3800, 0x300)
        sat_y0 = msx.read_debuggable("VRAM", 0x3B80, 1)[0]
        e11f = msx.read_byte(0xE11F)
        e120 = msx.read_byte(0xE120)
        ent = msx.read_memory(0xE300, 0x400)
        print(f"[init_screen_mode] hit={ok} pc=0x{int(msx.cmd('reg pc')):04X}")
        print(f"    name table 0x3800..0x3AFF all 0x20: "
              f"{all(b == 0x20 for b in name)} ({len(name)} bytes)")
        print(f"    SAT[0].Y @0x3B80 = 0x{sat_y0:02X} (expect 0xD0)")
        print(f"    sprite_count E11F = 0x{e11f:02X}, E120 = 0x{e120:02X} (expect 0)")
        print(f"    entity table 0xE300..0xE6FF all zero: "
              f"{all(b == 0 for b in ent)} ({len(ent)} bytes)")

        for bp in (bp_ds, bp_vr, bp_sm):
            msx.remove_breakpoint(bp)
        msx.cont()

if __name__ == "__main__":
    main()
