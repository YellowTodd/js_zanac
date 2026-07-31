#!/usr/bin/env python3
"""Sprint 0046 — Subsystem L (ending & credits): confirm remaining routines.

Phase A (ZanacGame, microexec):
  - compare_save_hiscore (0x4ACE): 3-byte score(E103) vs hiscore(E106); copies
    score->hiscore iff score >= hiscore.
  - init_credits_stream (0x9433): given a stream pointer, resolves the round into
    E701 and arms the stream state (E702/E704/E706, E700 bit0).
Phase B (ShotSession, -savestate game-end.oms):
  - credits_display (0x46D9): reached after the boss kill via E102 bit 3; saves
    hi-score on entry (0x46DD), renders the staff-roll text (PNG), and ESC -> title.

Run: .venv/bin/python tools/sprint0046_verify.py
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

def microexec(msx, entry, regs=None, timeout=2.5):
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
    out = {"AF": reg(msx, "AF")}
    msx.remove_breakpoint(bp)
    return out


def phase_a():
    with ZanacGame.launch("source/zanac.rom") as game:
        msx = game.client
        game.wait_for_title(); game.start_game(); time.sleep(1.0)
        game.make_invincible(); time.sleep(0.3)

        print("\n=== compare_save_hiscore (0x4ACE): copy score->hiscore iff >= ===")
        def run_hs(score, hiscore):
            msx.cmd("debug break")
            msx.write_memory(0xE103, bytes(score))    # E103/04/05 lo,mid,hi
            msx.write_memory(0xE106, bytes(hiscore))   # E106/07/08
            o = microexec(msx, 0x4ACE)
            hs = bytes(msx.read_memory(0xE106, 3))
            carry = o["AF"] & 0x01
            return hs, carry
        # score > hiscore -> hiscore becomes score, no carry
        hs, c = run_hs([0x00, 0x00, 0x10], [0x00, 0x00, 0x05])
        check("score>hiscore: hiscore<-score", hs == bytes([0, 0, 0x10]) and c == 0,
              f"hiscore={hs.hex()} C={c}")
        # score < hiscore -> unchanged, carry set
        hs, c = run_hs([0x00, 0x00, 0x01], [0x00, 0x00, 0x09])
        check("score<hiscore: hiscore unchanged (RET C)",
              hs == bytes([0, 0, 0x09]) and c == 1, f"hiscore={hs.hex()} C={c}")
        # equal -> copied (>= path), no carry
        hs, c = run_hs([0x42, 0x13, 0x07], [0x42, 0x13, 0x07])
        check("score==hiscore: >= path copies (no carry)",
              hs == bytes([0x42, 0x13, 0x07]) and c == 0, f"hiscore={hs.hex()} C={c}")

        print("\n=== init_credits_stream (0x9433): resolve round -> E701 + arm stream ===")
        # ending uses HL=0xBBB4; resolve_round_from_ptr(0xBBB4) -> 8 (above table top)
        before = bytes(msx.read_memory(0xE700, 8))
        msx.cmd("debug break")
        microexec(msx, 0x9433, {"HL": 0xBBB4}, timeout=3.0)
        e701 = msx.read_byte(0xE701)
        after = bytes(msx.read_memory(0xE700, 8))
        check("init_credits_stream sets E701 = resolved round (0xBBB4->8)",
              e701 == 8, f"E701=0x{e701:02X}")
        check("init_credits_stream arms stream state (E700 block changed)",
              after != before, f"E700..E707 {before.hex()} -> {after.hex()}")
        # null pointer -> immediate return (E701 untouched)
        msx.write_byte(0xE701, 0x55)
        microexec(msx, 0x9433, {"HL": 0x0000})
        check("init_credits_stream(HL=0) returns without touching E701",
              msx.read_byte(0xE701) == 0x55, f"E701=0x{msx.read_byte(0xE701):02X}")


def phase_b():
    from zanac_shot import ShotSession
    print("\n=== credits_display (0x46D9): entry, hi-score save, text, ESC->title ===")
    with ShotSession(savestate="savestates/game-end.oms") as s:
        msx = s.msx
        msx.cmd("debug break")
        msx.cmd("set ::cd 0; set ::hs 0")
        bp1 = msx.cmd("debug set_bp 0x46D9 true {incr ::cd}")     # credits entry
        bp2 = msx.cmd("debug set_bp 0x46DD true {incr ::hs}")     # hiscore save on entry
        msx.cont(); time.sleep(5.0); msx.cmd("debug break")
        cd = int(msx.cmd("set ::cd")); hs = int(msx.cmd("set ::hs"))
        msx.cmd(f"debug remove_bp {bp1}"); msx.cmd(f"debug remove_bp {bp2}")
        check("credits_display entry 0x46D9 reached after boss kill", cd >= 1, f"{cd} hits")
        check("hi-score save (0x46DD compare_save_hiscore) on credits entry",
              hs >= 1, f"{hs} hits")
        # screenshot of the running credits for visual text confirmation
        msx.cont(); time.sleep(2.0)
        png = "/tmp/zanac_credits.png"
        msx.cmd(f"screenshot -prefix {{}} {png}"); time.sleep(0.5)
        check("credits screenshot captured", pathlib.Path(png).exists(),
              f"{png} ({pathlib.Path(png).stat().st_size if pathlib.Path(png).exists() else 0} B)")

        # ESC -> title: hold ESC, break when the main loop restarts at 0x4042
        msx.cmd("debug break")
        msx.cmd("set ::title 0")
        bp = msx.cmd("debug set_bp 0x4042 true {incr ::title; debug break}")
        msx.key_down(7, 0x04)            # hold ESC (row 7 bit 2)
        msx.cont()
        t0 = time.time(); hit = False
        while time.time() - t0 < 18:
            if not msx.is_running() and int(msx.cmd("set ::title")) > 0:
                hit = True; break
            time.sleep(0.2)
        msx.key_up(7, 0x04)
        msx.cmd(f"debug remove_bp {bp}")
        check("ESC during credits -> title (0x4042)", hit, f"title-restart hit={hit}")
        png2 = "/tmp/zanac_after_esc.png"
        try:
            msx.cont(); time.sleep(1.5)
            msx.cmd(f"screenshot -prefix {{}} {png2}"); time.sleep(0.5)
        except Exception:
            pass


def main():
    phase_a()
    phase_b()
    print(f"\n==== {len(PASS)} passed, {len(FAIL)} failed ====")
    if FAIL:
        print("FAILED:", ", ".join(FAIL)); sys.exit(1)


if __name__ == "__main__":
    main()
