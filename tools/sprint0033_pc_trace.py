"""
Sprint 0033 — Sample PC every ~0.25 s while game runs from save state.
No breakpoints; just periodic reads of reg pc + key vars.
"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from zanackb.openmsx import OpenMsxClient
from zanackb.zanac_game import ZanacGame

ROM       = "source/zanac.rom"
IPS       = "scripts/invincible.ips"
SAVESTATE = "savestates/game-end.oms"

SAMPLE_INTERVAL = 0.25   # seconds between samples
DURATION        = 20.0   # total seconds to observe

def main():
    client, proc = OpenMsxClient.connect_subprocess(
        rom=ROM,
        extra_args=("-ips", IPS, "-savestate", SAVESTATE),
        timeout=30.0,
    )
    game = ZanacGame(client, proc)
    msx  = client
    try:
        msx.cmd("set ::cold 0")
        bp = msx.set_breakpoint(0x4010, "set ::cold 1")
        msx.power_on()
        msx.poll_flag("cold", interval=0.3, timeout=15.0)
        msx.remove_breakpoint(bp)

        print(f"{'Time':>6}  {'PC':>6}  {'E102':>6}  {'E700':>6}  {'E701':>6}  {'E712':>6}  {'E704':>8}")
        print(f"{'─'*6}  {'─'*6}  {'─'*6}  {'─'*6}  {'─'*6}  {'─'*6}  {'─'*8}")

        msx.cont()
        start = time.time()
        prev_pc = None

        while time.time() - start < DURATION:
            time.sleep(SAMPLE_INTERVAL)
            elapsed = time.time() - start

            # Read registers and key state using TCL (CPU is running, reads are non-invasive)
            pc   = int(msx.cmd("reg pc"))
            e102 = msx.read_byte(0xE102)
            e700 = msx.read_byte(0xE700)
            e701 = msx.read_byte(0xE701)
            e712 = msx.read_byte(0xE712)
            e704 = msx.read_byte(0xE704) | (msx.read_byte(0xE705) << 8)

            note = ""
            if prev_pc is not None and abs(pc - prev_pc) > 0x200:
                note = f"  ← PC jumped from 0x{prev_pc:04X}"
            prev_pc = pc

            print(f"{elapsed:6.2f}  0x{pc:04X}  0x{e102:02X}    0x{e700:02X}    "
                  f"0x{e701:02X}    0x{e712:02X}    0x{e704:04X}  {note}")

    finally:
        game.cleanup(); proc.terminate(); proc.wait()

if __name__ == "__main__":
    main()
