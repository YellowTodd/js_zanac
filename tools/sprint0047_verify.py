#!/usr/bin/env python3
"""Sprint 0047 — Subsystem N (HUD & status display): confirm render routines.

All checks are micro-exec: pause CPU, plant inputs, hijack PC to the routine,
trap on a stack sentinel (or a known exit address), then read back the VRAM the
routine wrote. The game is left halted between calls so VRAM stays stable.

Routines:
  render_score_bcd / render_lives_score (0x49B5 / 0x4996), render_score_row2
  (0x49AF), render_topscore_row2 (0x49A7), write_digit_to_vram (0x4B83),
  render_round_digit (0x4C68), update_status_bar (0x4C4D), render_hex_byte
  (0x4C74), add_score (0x4A74) + score_award_table (0x4AEA).

Run: .venv/bin/python tools/sprint0047_verify.py
"""
import sys, time, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "zanackb"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from zanackb.zanac_game import ZanacGame

ROM = open(pathlib.Path(__file__).resolve().parent.parent / "source/zanac.rom", "rb").read()
def romb(a): return ROM[a - 0x4000]

TRAP, SP = 0xE7F0, 0xEFFE
PASS, FAIL = [], []
def check(name, cond, detail):
    (PASS if cond else FAIL).append(name)
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}: {detail}")
def reg(msx, n, v=None):
    if v is None: return int(msx.cmd(f"reg {n}"))
    msx.cmd(f"reg {n} {v}")

def microexec(msx, entry, regs=None, exit_addr=None, timeout=2.0):
    """Run `entry`; stop at exit_addr if given, else at the stack-sentinel TRAP."""
    msx.cmd("debug break")
    target = exit_addr if exit_addr is not None else TRAP
    if exit_addr is None:
        msx.write_memory(SP, bytes([TRAP & 0xFF, TRAP >> 8]))
        reg(msx, "SP", SP)
    for r, v in (regs or {}).items(): reg(msx, r, v)
    reg(msx, "PC", entry)
    bp = msx.set_breakpoint(target, "debug break")
    msx.cont()
    t0 = time.time()
    while time.time() - t0 < timeout:
        if not msx.is_running() and reg(msx, "PC") == target: break
        time.sleep(0.01)
    msx.remove_breakpoint(bp)

def vram(msx, addr, n): return bytes(msx.read_debuggable("VRAM", addr, n))


def main():
    with ZanacGame.launch("source/zanac.rom") as game:
        msx = game.client
        game.wait_for_title(); game.start_game(); time.sleep(1.0)
        game.make_invincible(); time.sleep(0.3)

        print("\n=== render_lives_score (0x4996): score->0x3809, topscore->0x3815 ===")
        msx.write_memory(0xE103, bytes([0x56, 0x34, 0x12]))   # score  = 123456 BCD
        msx.write_memory(0xE106, bytes([0x21, 0x43, 0x65]))   # topsc  = 654321 BCD
        microexec(msx, 0x4996)
        sc = vram(msx, 0x3809, 6); tp = vram(msx, 0x3815, 6)
        check("score digits '123456' at 0x3809", sc == bytes(b"123456"),
              f"{sc!r}")
        check("topscore digits '654321' at 0x3815", tp == bytes(b"654321"),
              f"{tp!r}")

        print("\n=== render_score_row2 (0x49AF): score -> 0x3918 ===")
        microexec(msx, 0x49AF)
        check("score '123456' at 0x3918", vram(msx, 0x3918, 6) == bytes(b"123456"),
              f"{vram(msx, 0x3918, 6)!r}")

        print("\n=== render_topscore_row2 (0x49A7): topscore -> 0x38B8 ===")
        microexec(msx, 0x49A7)
        check("topscore '654321' at 0x38B8", vram(msx, 0x38B8, 6) == bytes(b"654321"),
              f"{vram(msx, 0x38B8, 6)!r}")

        print("\n=== leading-zero suppression (score = 000042) ===")
        msx.write_memory(0xE103, bytes([0x42, 0x00, 0x00]))
        microexec(msx, 0x49AF)
        got = vram(msx, 0x3918, 6)
        check("'    42' (leading zeros -> spaces)", got == b"    42", f"{got!r}")

        print("\n=== write_digit_to_vram (0x4B83): 2-digit decimal of A (tens+units) ===")
        microexec(msx, 0x4B83, {"A": 42, "HL": 0x3700})
        check("A=42 -> '42'", vram(msx, 0x3700, 2) == b"42", f"{vram(msx,0x3700,2)!r}")
        microexec(msx, 0x4B83, {"A": 5, "HL": 0x3710})
        check("A=5 -> ' 5' (leading-zero suppress)", vram(msx, 0x3710, 2) == b" 5",
              f"{vram(msx,0x3710,2)!r}")
        # 3-digit hundreds entry 0x4B8D (used for lives)
        microexec(msx, 0x0053, {"HL": 0x3730})
        microexec(msx, 0x4B8D, {"A": 137})
        check("0x4B8D A=137 -> '137' (3-digit entry)", vram(msx, 0x3730, 3) == b"137",
              f"{vram(msx,0x3730,3)!r}")

        print("\n=== render_round_digit (0x4C68): E701 -> 0x3A1B (2-digit) ===")
        msx.write_byte(0xE701, 5)
        microexec(msx, 0x4C68)
        check("round 5 -> ' 5' at 0x3A1B", vram(msx, 0x3A1B, 2) == b" 5",
              f"{vram(msx,0x3A1B,2)!r}")

        print("\n=== update_status_bar (0x4C4D): round+level+lives ===")
        msx.write_byte(0xE701, 7)    # round
        msx.write_byte(0xE10B, 3)    # shot_level
        msx.write_byte(0xE10A, 2)    # lives
        microexec(msx, 0x4C4D)
        rnd = vram(msx, 0x3A1B, 2); lvl = vram(msx, 0x39BB, 2); liv = vram(msx, 0x397A, 3)
        check("round 7 at 0x3A1B", rnd == b" 7", f"{rnd!r}")
        check("level 3 at 0x39BB", lvl == b" 3", f"{lvl!r}")
        check("lives shows a digit at 0x397A", liv[-1:].isdigit(), f"{liv!r}")

        print("\n=== render_hex_byte (0x4C74): 2 hex digits (needs SETWRT first) ===")
        for val, exp in [(0xAB, b"AB"), (0x3C, b"3C"), (0x07, b"07")]:
            microexec(msx, 0x0053, {"HL": 0x3720})      # SETWRT(0x3720)
            microexec(msx, 0x4C74, {"A": val})
            got = vram(msx, 0x3720, 2)
            check(f"render_hex_byte 0x{val:02X} -> {exp!r}", got == exp, f"{got!r}")

        print("\n=== add_score (0x4A74) + score_award_table (0x4AEA) ===")
        for idx in (1, 9, 13):
            msx.write_memory(0xE103, bytes([0, 0, 0]))    # score = 0
            microexec(msx, 0x4A74, {"A": idx}, exit_addr=0x4A26)
            sc = bytes(msx.read_memory(0xE103, 3))         # lo,mid,hi BCD
            tbl = bytes(romb(0x4AEA + idx * 3 + k) for k in range(3))
            check(f"add_score(idx={idx}) adds table[idx]={tbl.hex()}",
                  sc == tbl, f"score={sc.hex()} exp={tbl.hex()}")

        print("\n=== draw_hud_labels (0x4BD4): writes static labels ===")
        # wipe a HUD label region, redraw, confirm it became non-blank
        msx.cmd("debug break")
        # SETWRT 0x38F9 + fill 6 spaces via FILVRM(0x0056): A=0x20, HL=0x38F9, BC=6
        microexec(msx, 0x0053, {"HL": 0x38F9})
        before = vram(msx, 0x38F9, 6)
        microexec(msx, 0x4BD4, timeout=3.0)
        after = vram(msx, 0x38F9, 6)
        check("draw_hud_labels writes HUD label tiles", any(b not in (0, 0x20) for b in after),
              f"0x38F9: {before.hex()} -> {after.hex()} ({after!r})")


    print(f"\n==== {len(PASS)} passed, {len(FAIL)} failed ====")
    if FAIL:
        print("FAILED:", ", ".join(FAIL)); sys.exit(1)


if __name__ == "__main__":
    main()
