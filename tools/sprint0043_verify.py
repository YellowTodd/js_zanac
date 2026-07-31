#!/usr/bin/env python3
"""Sprint 0043 — Subsystem B (frame/render pipeline): confirm all routines.

Micro-execution harness: pause CPU, set up input registers, hijack PC to the
routine entry, place a return-trap (RET pops a sentinel address we breakpoint),
run, read outputs. Pure/near-pure routines are unit-tested this way. The wait
primitives, sprite_shadow_push, and the SAT-DMA path are checked live.

Run: .venv/bin/python tools/sprint0043_verify.py
"""
import sys, time, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "zanackb"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from zanackb.zanac_game import ZanacGame, MSXKey

TRAP = 0xE7F0          # sentinel return address (unused RAM); we break here
SP   = 0xEFFE          # scratch stack top


def reg(msx, name, val=None):
    if val is None:
        return int(msx.cmd(f"reg {name}"))
    msx.cmd(f"reg {name} {val}")
    return None


def microexec(msx, entry, regs=None, timeout=2.0):
    """Run `entry` once with given regs; stop when it RETs to TRAP. Returns dict
    of output registers after the trap."""
    msx.cmd("debug break")
    # plant trap return address (little-endian) at SP, point SP there
    msx.write_memory(SP, bytes([TRAP & 0xFF, (TRAP >> 8) & 0xFF]))
    reg(msx, "SP", SP)
    for r, v in (regs or {}).items():
        reg(msx, r, v)
    reg(msx, "PC", entry)
    bp = msx.set_breakpoint(TRAP, "debug break")
    msx.cont()
    t0 = time.time()
    while time.time() - t0 < timeout:
        if not msx.is_running():
            if reg(msx, "PC") == TRAP:
                break
            msx.cont()  # hit some other break (shouldn't); resume
        time.sleep(0.01)
    out = {r: reg(msx, r) for r in ("AF", "BC", "DE", "HL", "PC", "SP")}
    msx.remove_breakpoint(bp)
    return out


PASS = []
FAIL = []


def check(name, cond, detail):
    (PASS if cond else FAIL).append(name)
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}: {detail}")


def main():
    with ZanacGame.launch("source/zanac.rom") as game:
        msx = game.client
        game.wait_for_title()
        game.start_game()
        time.sleep(1.0)
        game.make_invincible()
        time.sleep(0.5)

        # ── LIVE CHECKS FIRST (game must be healthy; microexec corrupts PC/SP) ──
        print("\n=== sprite_shadow_push (0x48A9): prove fall-through path executes ===")
        msx.cmd("debug break")
        msx.cmd("set ::ssp 0")
        bp = msx.set_breakpoint(0x48A9, "incr ::ssp")
        msx.cont(); time.sleep(0.5); msx.cmd("debug break")
        hits = int(msx.cmd("set ::ssp"))
        msx.remove_breakpoint(bp)
        check("sprite_shadow_push 0x48A9 reached via entity_update fall-through",
              hits > 0, f"{hits} executions in 0.5s")

        print("\n=== sat_dma_to_vram (ISR 0x43F8-0x4448): live 0xE000 vs VRAM 0x3B80 ===")
        msx.cont(); time.sleep(0.5); msx.cmd("debug break")
        shadow = msx.read_memory(0xE000, 128)
        vram = msx.read_debuggable("VRAM", 0x3B80, 128)
        match = sum(1 for a, b in zip(shadow, vram) if a == b)
        check("SAT shadow 0xE000 == VRAM 0x3B80 (DMA path)", match >= 118,
              f"{match}/128 bytes match")

        print("\n=== frame_counter 0xE1F8 driven by ISR ===")
        msx.cmd("set ::vbl 0")
        wvbl = msx.cmd("debug set_watchpoint write_mem 0xe1f8 {} {incr ::vbl}")
        msx.cont(); time.sleep(0.2); msx.cmd("debug break")
        inc = int(msx.cmd("set ::vbl"))
        msx.remove_watchpoint(wvbl)
        check("frame_counter 0xE1F8 written each frame (ISR + wait loops)", inc >= 8,
              f"{inc} writes in 0.2s")

        # ── MICROEXEC UNIT TESTS LAST (leaves CPU hijacked; we quit after) ──
        print("\n=== tile_to_vram_addr (0x5BDD): (col=H, row=L) -> name-table addr ===")
        # name table base 0x3800; addr = 0x3800 + row*32 + col
        for col, row in [(0, 0), (5, 3), (31, 23), (10, 10)]:
            o = microexec(msx, 0x5BDD, {"H": col, "L": row})
            exp = 0x3800 + row * 32 + col
            check(f"tile_to_vram_addr col={col},row={row}", o["HL"] == exp,
                  f"HL=0x{o['HL']:04X} exp=0x{exp:04X}")

        print("\n=== vdp_write_byte_di (0x5BFC): SETWRT then stream A to VRAM ===")
        for vaddr, val in [(0x3A00, 0x5A), (0x3A01, 0xC3), (0x3A40, 0x7E)]:
            microexec(msx, 0x0053, {"HL": vaddr})          # SETWRT(vaddr)
            microexec(msx, 0x5BFC, {"A": val})              # write byte
            got = msx.read_debuggable("VRAM", vaddr, 1)[0]
            check(f"vdp_write_byte_di @0x{vaddr:04X}", got == val,
                  f"VRAM=0x{got:02X} exp=0x{val:02X}")

        print("\n=== vdp_int_disable (0x42ED) / vdp_int_enable (0x42F8): R1 IE bit5 ===")
        r1 = msx.read_byte(0xF3E0)
        microexec(msx, 0x42ED)                              # disable
        d = msx.read_byte(0xF3E0)
        microexec(msx, 0x42F8)                              # enable
        e = msx.read_byte(0xF3E0)
        check("vdp_int_disable clears R1 bit5", (d & 0x20) == 0, f"R1=0x{d:02X}")
        check("vdp_int_enable sets R1 bit5", (e & 0x20) != 0, f"R1=0x{e:02X}")

        print("\n=== disable_display (0x42D7) / enable_display (0x42E2): R1 BL bit6 ===")
        microexec(msx, 0x42D7)
        d = msx.read_byte(0xF3E0)
        microexec(msx, 0x42E2)
        e = msx.read_byte(0xF3E0)
        check("disable_display clears R1 bit6", (d & 0x40) == 0, f"R1=0x{d:02X}")
        check("enable_display sets R1 bit6", (e & 0x40) != 0, f"R1=0x{e:02X}")

        print("\n=== sprite_sat_write (0x48B8): append 4-byte SAT entry, advance 0xE122 ===")
        # build a fake entity slot in scratch RAM and point IX at it
        slot = 0xE780
        # slot[1]=Y(bottom), slot[2]=X, slot[3]=name, slot[4]=colour
        msx.write_memory(slot, bytes([0x00, 0x64, 0x50, 0x38, 0x0F]))
        wp0 = 0xE000 + 4 * 7   # pretend 7 entries already written
        msx.write_memory(0xE122, bytes([wp0 & 0xFF, (wp0 >> 8) & 0xFF]))
        microexec(msx, 0x48B8, {"IX": slot})
        shadow = msx.read_memory(wp0, 4)
        wp1 = msx.read_byte(0xE122) | (msx.read_byte(0xE123) << 8)
        check("sprite_sat_write SAT Y = slot[1]-0x11", shadow[0] == (0x64 - 0x11),
              f"shadow[0]=0x{shadow[0]:02X}")
        check("sprite_sat_write SAT X/name/col copied",
              shadow[1] == 0x50 and shadow[2] == 0x38 and shadow[3] == 0x0F,
              f"shadow[1..3]={shadow[1:].hex()}")
        check("sprite_sat_write advances 0xE122 by 4", wp1 == wp0 + 4,
              f"E122=0x{wp1:04X} exp=0x{wp0 + 4:04X}")

        print("\n=== wait_one_frame (0x4306): returns 1 frame later, zeroes 0xE1F8 ===")
        msx.cmd("debug break")
        # trap-based: call wait_one_frame, ensure it returns (doesn't hang) and
        # that 0xE1F8 is 0 on return (it zeroes the counter).
        microexec(msx, 0x4306, timeout=2.0)
        fc = msx.read_byte(0xE1F8)
        check("wait_one_frame returns & zeroes 0xE1F8", fc == 0, f"0xE1F8=0x{fc:02X}")

        # wait_frames(B): must block ~B frames then return. Time it for B=20.
        msx.cmd("debug break")
        t0 = time.time()
        microexec(msx, 0x5BEC, {"B": 20}, timeout=3.0)
        dt = time.time() - t0
        # 20 frames @59Hz ≈ 0.34s; wall-clock includes poll overhead, allow margin
        check("wait_frames(20) blocks ~20 frames then returns", 0.20 <= dt <= 1.5,
              f"elapsed {dt:.2f}s (exp ~0.34s)")

    print(f"\n==== {len(PASS)} passed, {len(FAIL)} failed ====")
    if FAIL:
        print("FAILED:", ", ".join(FAIL))
        sys.exit(1)


if __name__ == "__main__":
    main()
