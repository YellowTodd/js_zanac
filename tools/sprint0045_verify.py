#!/usr/bin/env python3
"""Sprint 0045 — Subsystem K (game-flow state machine): confirm flag map + rounds.

Phase A (ZanacGame, stdio control):
  - Round selector: warp to rounds 1/3/8, confirm E701 == round; confirm E110
    stays 0x01 (so E110 is NOT the round — corrects game_state_block).
  - Game-over path: inject E102 bit 1 in-game, confirm game_over_handler sets
    bit 7 (go_to_title) and writes "GAME OVER" to VRAM 0x3987.
  - sub_9444 (round resolver) microexec: map each stream-start pointer in the
    table at 0x945C to its round index; the ending pointer 0xA6F4 -> 0.
Phase B (ShotSession, -savestate): end-of-round-8 state transition through the
  level_complete -> credits path.

Run: .venv/bin/python tools/sprint0045_verify.py
"""
import sys, time, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "zanackb"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from zanackb.zanac_game import ZanacGame

ROM = open(pathlib.Path(__file__).resolve().parent.parent / "source/zanac.rom", "rb").read()
def romw(a): return ROM[a - 0x4000] | (ROM[a - 0x4000 + 1] << 8)

TRAP, SP = 0xE7F0, 0xEFFE
PASS, FAIL = [], []
def check(name, cond, detail):
    (PASS if cond else FAIL).append(name)
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}: {detail}")

def reg(msx, n, v=None):
    if v is None: return int(msx.cmd(f"reg {n}"))
    msx.cmd(f"reg {n} {v}")

def microexec(msx, entry, regs=None, timeout=2.0):
    msx.cmd("debug break")
    msx.write_memory(SP, bytes([TRAP & 0xFF, TRAP >> 8]))
    reg(msx, "SP", SP)
    for r, v in (regs or {}).items(): reg(msx, r, v)
    reg(msx, "PC", entry)
    bp = msx.set_breakpoint(TRAP, "debug break")
    msx.cont()
    t0 = time.time()
    while time.time() - t0 < timeout:
        if not msx.is_running() and reg(msx, "PC") == TRAP: break
        time.sleep(0.01)
    out = {r: reg(msx, r) for r in ("AF", "HL")}
    msx.remove_breakpoint(bp)
    return out


def phase_a():
    with ZanacGame.launch("source/zanac.rom") as game:
        msx = game.client

        print("\n=== round selector: E701 == warp round; E110 is NOT round ===")
        for rnd in (1, 3, 8):
            game.wait_for_title(); game.arm_warp(rnd); game.start_game()
            time.sleep(1.2)
            e701 = msx.read_byte(0xE701); e110 = msx.read_byte(0xE110)
            check(f"warp r{rnd}: E701==round", e701 == rnd, f"E701=0x{e701:02X}")
            check(f"warp r{rnd}: E110 stays 0x01 (not round)", e110 == 0x01,
                  f"E110=0x{e110:02X}")
            msx.cmd("reset"); time.sleep(1.8)

        print("\n=== game-over path: E102 bit1 -> bit7 + 'GAME OVER' VRAM ===")
        game.wait_for_title(); game.arm_warp(1); game.start_game()
        time.sleep(1.0); game.make_invincible(); time.sleep(0.3)
        msx.write_byte(0xE102, msx.read_byte(0xE102) | 0x02)   # set game_over
        time.sleep(0.5)
        e102 = msx.read_byte(0xE102)
        # "GAME OVER" written at VRAM 0x3987 (Screen-2 name table)
        vram = bytes(msx.read_debuggable("VRAM", 0x3987, 11))
        # tiles are ASCII-ish font indices; check it's non-blank (changed from 0)
        nonblank = sum(1 for b in vram if b not in (0x00, 0x20))
        check("game_over_handler sets E102 bit7 (go_to_title)", (e102 & 0x80) != 0,
              f"E102=0x{e102:02X}")
        check("'GAME OVER' written to VRAM 0x3987", nonblank >= 6,
              f"VRAM={vram.hex()} ({nonblank} non-blank)")

        print("\n=== sub_9444: stream pointer -> round index (microexec, last) ===")
        # table at 0x945C: 8 LE words; entry[i] is round (8-i)'s stream start.
        entries = [romw(0x945C + 2 * i) for i in range(8)]
        allok = True
        for i, ptr in enumerate(entries):
            o = microexec(msx, 0x9444, {"HL": ptr})
            rnd = (o["AF"] >> 8) & 0xFF
            exp = 8 - i
            ok = rnd == exp
            allok &= ok
            print(f"    0x{ptr:04X} -> round {rnd} (exp {exp}) {'ok' if ok else 'BAD'}")
        check("sub_9444 maps each table entry to its round", allok,
              f"{len(entries)} entries 0x{entries[0]:04X}..0x{entries[-1]:04X}")
        # ending pointer below the table -> round 0
        o = microexec(msx, 0x9444, {"HL": 0xA6F4})
        rnd = (o["AF"] >> 8) & 0xFF
        check("sub_9444(0xA6F4 ending ptr) -> 0", rnd == 0, f"got {rnd}")


def phase_b():
    from zanac_shot import ShotSession
    print("\n=== end-of-round-8 (savestate): level_complete -> credits ===")
    with ShotSession(savestate="savestates/game-end.oms") as s:
        msx = s.msx
        msx.cmd("debug break")
        e102_0 = msx.read_byte(0xE102); e701_0 = msx.read_byte(0xE701)
        e722 = msx.read_byte(0xE722) | (msx.read_byte(0xE723) << 8)
        check("at boss-kill: E102 bits 5+3 set (level_complete+credits)",
              (e102_0 & 0x28) == 0x28, f"E102=0x{e102_0:02X}")
        check("at boss-kill: E701=8, E722=0xA6F4 (ending stream ptr)",
              e701_0 == 8 and e722 == 0xA6F4, f"E701=0x{e701_0:02X} E722=0x{e722:04X}")
        msx.cont(); time.sleep(4.0); msx.cmd("debug break")
        e102_1 = msx.read_byte(0xE102); e701_1 = msx.read_byte(0xE701)
        check("after transition: E701 -> 0 (sub_9444 mapped ending ptr)",
              e701_1 == 0, f"E701=0x{e701_1:02X}")
        check("after transition: bit5 cleared, bit3 (credits) still set",
              (e102_1 & 0x20) == 0 and (e102_1 & 0x08) == 0x08, f"E102=0x{e102_1:02X}")
        msx.cont()


def main():
    phase_a()
    phase_b()
    print(f"\n==== {len(PASS)} passed, {len(FAIL)} failed ====")
    if FAIL:
        print("FAILED:", ", ".join(FAIL)); sys.exit(1)


if __name__ == "__main__":
    main()
