#!/usr/bin/env python3
"""Confirm check_start_key (0x43D2) is the ESC check that drives the E701 branch.

Key mapping is confirmed separately (keymatrix: ESC = row 7 bit 2). Here, at the
call site in title_screen_init we plant an E701 sentinel (=5), force a clean
row-7 state (all released, then optionally press ESC), and observe:
  - at 0x43D9 (RET): reg A = SNSMAT row 7, F's Z flag set by `BIT 2,A`
  - at 0x425A (after the JR Z branch): E701 reset to 1 (ESC up) or retained (held)
"""
import sys
sys.path.insert(0, "tools")
from zanackb.zanac_game import ZanacGame

def one_boot(esc_held: bool):
    label = "ESC HELD" if esc_held else "ESC up  "
    with ZanacGame.launch("source/zanac.rom") as game:
        msx = game.client
        msx.cmd("set ::b1 0")
        bp1 = msx.set_breakpoint(0x424C, "set ::b1 1; debug break")
        msx.reset()
        msx.poll_flag("b1", interval=0.2, timeout=15.0)
        # force a clean row-7 matrix state
        msx.cmd("keymatrixup 7 255")          # release all row-7 keys
        if esc_held:
            msx.cmd("keymatrixdown 7 4")      # press ESC (bit 2)
        row7 = msx.read_debuggable("keymatrix", 7, 1)[0]
        msx.write_byte(0xE701, 5)             # sentinel
        msx.remove_breakpoint(bp1)

        msx.cmd("set ::b2 0")
        bp2 = msx.set_breakpoint(0x43D9, "set ::b2 1; debug break")
        msx.cont()
        msx.poll_flag("b2", interval=0.2, timeout=15.0)
        a = int(msx.cmd("reg a"))
        f = int(msx.cmd("reg f"))
        z = (f >> 6) & 1
        msx.remove_breakpoint(bp2)

        msx.cmd("set ::b3 0")
        bp3 = msx.set_breakpoint(0x425A, "set ::b3 1; debug break")
        msx.cont()
        msx.poll_flag("b3", interval=0.2, timeout=15.0)
        e701 = msx.read_byte(0xE701)
        msx.remove_breakpoint(bp3)

        print(f"[{label}] keymatrix row7=0x{row7:02X} -> SNSMAT A=0x{a:02X} "
              f"bit2={(a>>2)&1} Z={z}  =>  E701={e701} "
              f"({'retained=continue' if e701 == 5 else 'reset to '+str(e701)})")

if __name__ == "__main__":
    one_boot(False)
    one_boot(True)
