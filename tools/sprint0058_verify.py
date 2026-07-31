#!/usr/bin/env python3
"""Sprint 0058 — Subsystem M (Secrets & warps): confirm the ESC-continue /
round-0 warp mechanism and capture the "secret round 0" content.

Checks:
  1. stage_stream_ptr_table (0x945C): E701=0 selects entry index 8 (=8-E701)
     -> stream pointer 0xA65C (ROM read, no gameplay needed).
  2. warp.tcl mechanism: break at 0x425A, force E701=0 before the level-stream
     engine reads it, start the game, and confirm E701 stayed 0 and the round
     HUD digit shows 0. Screenshot the resulting stage.

Run (needs $DISPLAY for the SDL screenshot):
  .venv/bin/python tools/sprint0058_verify.py [/tmp/round0.png]
"""
import os, sys, time, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from zanac_shot import ShotSession

ROM = open(pathlib.Path(__file__).resolve().parent.parent / "source/zanac.rom", "rb").read()
def romw(a):  # little-endian word from ROM (page-2 cart at 0x4000)
    return ROM[a - 0x4000] | (ROM[a - 0x4000 + 1] << 8)

OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/round0.png"


def main():
    # --- Static check 1: level-start table entry for round 0 ---
    tbl = 0x945C
    # index = 8 - E701; E701=0 -> index 8 -> pointer at tbl + 8*2
    ptr0 = romw(tbl + 8 * 2)
    print(f"stage_stream_ptr_table[8] (E701=0) = 0x{ptr0:04X}  (expect 0xA65C)")
    assert ptr0 == 0xA65C, f"unexpected round-0 stream pointer 0x{ptr0:04X}"

    # --- Live check 2: warp to round 0 via the 0x425A title breakpoint ---
    with ShotSession() as s:
        msx = s.msx
        msx.cmd("debug break")
        # one-shot: at LAB_425a force E701 = 0, then let it run
        msx.cmd("set ::m_hit 0")
        bp = msx.cmd("debug set_bp 0x425A {} "
                     "{ debug write memory 0xE701 0; incr ::m_hit; debug cont }")
        msx.cont()
        # wait out the MSX BIOS boot + Zanac title fade-in
        time.sleep(8.0)
        # press SPACE at the title to start; the bp fires inside title_screen_init
        for _ in range(6):
            msx.key_down(8, 0x01)   # SPACE (row 8 bit 0)
            time.sleep(0.4)
            msx.key_up(8, 0x01)
            time.sleep(0.4)
            if int(msx.cmd("set ::m_hit")) > 0:
                break
        time.sleep(3.0)

        hit = int(msx.cmd("set ::m_hit"))
        e701 = msx.read_byte(0xE701)
        e102 = msx.read_byte(0xE102)
        e700 = msx.read_byte(0xE700)
        print(f"bp hits at 0x425A = {hit}")
        print(f"E701 (round)   = {e701}   (expect 0)")
        print(f"E700/E102      = 0x{e700:02X} / 0x{e102:02X}")

        s.shot(OUT)
        time.sleep(0.5)
        try:
            msx.remove_breakpoint(bp)
        except Exception:
            pass
        print(f"screenshot -> {OUT}  exists={os.path.exists(OUT)} "
              f"size={os.path.getsize(OUT) if os.path.exists(OUT) else '-'}")


if __name__ == "__main__":
    main()
