#!/usr/bin/env python3
"""Sprint 0059 — Subsystem M warp orbs: confirm the idol→orb→warp mechanism.

Two live checks against real gameplay:

  A. Orb effect tail (type-72, 0x89EF): micro-exec the "player touched me"
     branch with +0x1E forced to 0 (black orb) and +0x1C/1D = a chosen stream
     pointer. Confirm it writes E722 = that pointer and sets E102 bit 5.
     Repeat with +0x1E != 0 (yellow orb) and confirm it does NOT write E722
     (kill-all-enemies path via explode_enemies instead).

  B. E722 -> round: set E722 = round-5 stream (0xB1DE) + E102 bit 5 during
     round-1 play, let level_complete_handler run, confirm E701 -> 5.

Run: .venv/bin/python tools/sprint0059_verify.py
"""
import sys, time, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from zanackb.zanac_game import ZanacGame

TRAP, SP = 0xE7F0, 0xEFFE
SLOT = 0xE320                      # scratch entity slot (enemy slot 1)

def reg(msx, n, v=None):
    if v is None: return int(msx.cmd(f"reg {n}"))
    msx.cmd(f"reg {n} {v}")

def microexec(msx, entry, exit_addr, timeout=2.0):
    msx.cmd("debug break")
    msx.write_memory(SP, bytes([TRAP & 0xFF, TRAP >> 8]))
    reg(msx, "SP", SP)
    reg(msx, "PC", entry)
    reg(msx, "IX", SLOT)
    bp = msx.set_breakpoint(exit_addr, "debug break")
    msx.cont()
    t0 = time.time()
    while time.time() - t0 < timeout:
        if not msx.is_running() and reg(msx, "PC") == exit_addr: break
        time.sleep(0.01)
    hit = (not msx.is_running() and reg(msx, "PC") == exit_addr)
    msx.remove_breakpoint(bp)
    return hit


def main():
    with ZanacGame.launch("source/zanac.rom") as game:
        msx = game.client
        game.wait_for_title(); game.start_game(); time.sleep(1.0)
        game.make_invincible(); time.sleep(0.3)

        print("=== A. Orb effect tail 0x89EF (black orb, +0x1E=0) ===")
        # +0x1C/1D at SLOT+0x1C/0x1D = 0xAD61 (round-3 stream); +0x1E=0
        msx.write_byte(0xE102, 0x00)
        msx.write_byte(0xE722, 0x00); msx.write_byte(0xE723, 0x00)
        msx.write_byte(SLOT + 0x1C, 0x61)
        msx.write_byte(SLOT + 0x1D, 0xAD)
        msx.write_byte(SLOT + 0x1E, 0x00)          # black
        ok = microexec(msx, 0x89EF, 0x48D0)
        e722 = msx.read_byte(0xE722) | (msx.read_byte(0xE723) << 8)
        e102 = msx.read_byte(0xE102)
        print(f"  reached entity_clear={ok}  E722=0x{e722:04X} (expect 0xAD61)  "
              f"E102=0x{e102:02X} bit5={'set' if e102 & 0x20 else 'CLEAR'}")

        print("=== A'. Orb effect tail 0x89EF (yellow orb, +0x1E=1) ===")
        msx.write_byte(0xE102, 0x00)
        msx.write_byte(0xE722, 0x00); msx.write_byte(0xE723, 0x00)
        msx.write_byte(SLOT + 0x1C, 0x61)
        msx.write_byte(SLOT + 0x1D, 0xAD)
        msx.write_byte(SLOT + 0x1E, 0x01)          # yellow
        ok = microexec(msx, 0x89EF, 0x48D0)
        e722 = msx.read_byte(0xE722) | (msx.read_byte(0xE723) << 8)
        e102 = msx.read_byte(0xE102)
        print(f"  reached entity_clear={ok}  E722=0x{e722:04X} (expect 0x0000)  "
              f"E102=0x{e102:02X} bit5={'set' if e102 & 0x20 else 'clear'} "
              f"(yellow => kill-all, no warp)")

        print("=== B. E722=0xB1DE (round 5) + bit5 -> E701 ===")
        msx.cont(); time.sleep(0.2)
        r_before = msx.read_byte(0xE701)
        msx.write_byte(0xE722, 0xDE); msx.write_byte(0xE723, 0xB1)
        msx.write_byte(0xE102, msx.read_byte(0xE102) | 0x20)
        time.sleep(3.0)
        r_after = msx.read_byte(0xE701)
        print(f"  E701 before={r_before}  after={r_after}  (expect 5)")


if __name__ == "__main__":
    main()
