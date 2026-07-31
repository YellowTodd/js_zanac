#!/usr/bin/env python3
"""Sprint 0044 — Subsystem C (entity framework): confirm remaining routines.

Live traces (game stays healthy throughout — no PC/SP hijack):
  - entity_dispatch (0x445F): hit count; capture (type -> handler) at the JP HL
    site (0x4486) and check each against ROM jump table 0x70B7 + type*2; confirm
    0xE11F written from 0xE122 low byte.
  - entity_update (0x4898): hit count; spawn a homing enemy (type 10 duster,
    bflags 0x13 = Y+X+X-homing) and confirm the homing subs 0x4942/0x496B fire.
  - collision_dispatch (0x44D4) / collision_response (0x453E): drive shots into
    enemies; confirm 0x453E fires and remaps both parties' type bytes through
    the transition table at 0x716B.

Run: .venv/bin/python tools/sprint0044_verify.py
"""
import sys, time, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "zanackb"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from zanackb.zanac_game import ZanacGame

ROM = open(pathlib.Path(__file__).resolve().parent.parent / "source/zanac.rom", "rb").read()
def romw(addr):  # little-endian word from ROM (cart base 0x4000)
    o = addr - 0x4000
    return ROM[o] | (ROM[o + 1] << 8)
def romb(addr):
    return ROM[addr - 0x4000]

PASS, FAIL = [], []
def check(name, cond, detail):
    (PASS if cond else FAIL).append(name)
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}: {detail}")


def hitcount(msx, addr, secs=0.5):
    msx.cmd("debug break"); msx.cmd("set ::hc 0")
    bp = msx.cmd(f"debug set_bp 0x{addr:04X} true {{incr ::hc}}")
    msx.cont(); time.sleep(secs); msx.cmd("debug break")
    n = int(msx.cmd("set ::hc"))
    msx.cmd(f"debug remove_bp {bp}")
    return n


def main():
    with ZanacGame.launch("source/zanac.rom") as game:
        msx = game.client
        game.wait_for_title(); game.start_game(); time.sleep(1.0)
        game.make_invincible(); time.sleep(0.3)

        print("\n=== entity_dispatch (0x445F): runs every frame ===")
        n = hitcount(msx, 0x445F, 0.5)
        check("entity_dispatch executes (~30/0.5s)", n >= 10, f"{n} calls/0.5s")

        print("\n=== entity_dispatch: (type -> handler) matches ROM table 0x70B7+2*type ===")
        # capture at JP HL (0x4486): A' is gone, but A holds type*2 already; grab
        # the slot type from IX+0 and the resolved handler from HL.
        msx.cmd("debug break")
        msx.cmd("set ::n 0; array unset ::ty; array unset ::hl")
        bp = msx.cmd(
            "debug set_bp 0x4486 true {"
            "set ::ty($::n) [debug read memory [reg IX]]; "
            "set ::hl($::n) [reg HL]; incr ::n}")
        msx.cont(); time.sleep(0.5); msx.cmd("debug break")
        n = int(msx.cmd("set ::n"))
        seen = {}
        for i in range(n):
            t = int(msx.cmd(f"set ::ty($::n_{i})")) if False else int(msx.cmd(f"set ::ty({i})"))
            h = int(msx.cmd(f"set ::hl({i})"))
            seen.setdefault(t, h)
        msx.cmd(f"debug remove_bp {bp}")
        # dispatcher does ADD A,A on the full type byte (bit 7 shifts out), so the
        # index is (type*2)&0xFF == (type&0x7F)*2; handler = *(0x70B7 + that)
        def expect(t):
            return romw(0x70B7 + ((t * 2) & 0xFF))
        ok = all(h == expect(t) for t, h in seen.items())
        sample = ", ".join(f"t{t & 0x7F}->0x{h:04X}" for t, h in list(seen.items())[:6])
        check("dispatched handler == ROM jump table", ok and len(seen) > 0,
              f"{len(seen)} distinct types; {sample}")

        print("\n=== entity_dispatch: 0xE11F (sprite byte count) = 0xE122 low ===")
        msx.cmd("debug break")
        bp = msx.cmd("debug set_bp 0x448F true {debug break}")  # after loop, before store
        msx.cont()
        t0 = time.time()
        while time.time() - t0 < 2:
            if not msx.is_running():
                break
            time.sleep(0.01)
        time.sleep(0.05)
        e122lo = msx.read_byte(0xE122)
        msx.cont(); time.sleep(0.05); msx.cmd("debug break")
        e11f = msx.read_byte(0xE11F)
        msx.cmd(f"debug remove_bp {bp}")
        check("0xE11F = active_sprites*4 (= 0xE122 low at loop end)",
              e11f == e122lo, f"0xE11F=0x{e11f:02X} 0xE122lo=0x{e122lo:02X}")

        print("\n=== entity_update (0x4898): runs on entity hot path ===")
        n = hitcount(msx, 0x4898, 0.5)
        check("entity_update executes", n >= 5, f"{n} calls/0.5s")

        print("\n=== entity_update: homing branch (spawn type 10 duster, bflags 0x13) ===")
        msx.cmd("debug break")
        msx.cmd("set ::yh 0; set ::xh 0")
        bpy = msx.cmd("debug set_bp 0x4942 true {incr ::yh}")
        bpx = msx.cmd("debug set_bp 0x496B true {incr ::xh}")
        msx.cont()
        for _ in range(4):
            game.spawn_type(0x0A, y=60, x=120)   # duster: Y+X+X-homing
            time.sleep(0.4)
        time.sleep(0.4); msx.cmd("debug break")
        yh = int(msx.cmd("set ::yh")); xh = int(msx.cmd("set ::xh"))
        msx.cmd(f"debug remove_bp {bpy}"); msx.cmd(f"debug remove_bp {bpx}")
        check("entity_update routes X-homing (0x496B) for bit-4 entities",
              xh > 0, f"X-homing fired {xh}x, Y-homing {yh}x")

        print("\n=== collision_dispatch (0x44D4): runs on collision-test path ===")
        n = hitcount(msx, 0x44D4, 0.5)
        check("collision_dispatch executes", n >= 1, f"{n} calls/0.5s")

        print("\n=== collision_response (0x453E): type remap via table 0x716B ===")
        # drive shots into spawned enemies until 0x453E fires; capture remap
        msx.cmd("debug break")
        msx.cmd("set ::cr 0; array unset ::ix0; array unset ::iy0; "
                "array unset ::ixt; array unset ::iyt")
        bp = msx.cmd(
            "debug set_bp 0x453E true {"
            "set ::ixt($::cr) [expr {[debug read memory [reg IX]] & 0x7f}]; "
            "set ::iyt($::cr) [expr {[debug read memory [reg IY]] & 0x7f}]; "
            "incr ::cr}")
        # capture the *result* just after RET (0x455F) too
        bp2 = msx.cmd(
            "set ::k 0; debug set_bp 0x455F true {"
            "set ::ix0($::k) [debug read memory [reg IX]]; "
            "set ::iy0($::k) [debug read memory [reg IY]]; incr ::k}")
        msx.cont()
        # spawn enemies in front of the ship and fire continuously
        for _ in range(20):
            if int(msx.cmd("set ::cr")) >= 3:
                break
            game.spawn_type(0x04, y=70, x=124)   # box enemy near player
            game.fire_shot(0.05)
            game.shoot_shot()
            time.sleep(0.25)
        game.release_shot()
        time.sleep(0.2); msx.cmd("debug break")
        cr = int(msx.cmd("set ::cr")); k = int(msx.cmd("set ::k"))
        results = []
        for i in range(min(cr, k)):
            ixt = int(msx.cmd(f"set ::ixt({i})")); iyt = int(msx.cmd(f"set ::iyt({i})"))
            ix0 = int(msx.cmd(f"set ::ix0({i})")); iy0 = int(msx.cmd(f"set ::iy0({i})"))
            results.append((ixt, ix0, iyt, iy0))
        msx.cmd(f"debug remove_bp {bp}"); msx.cmd(f"debug remove_bp {bp2}")
        check("collision_response fires on shot-vs-enemy", cr > 0, f"{cr} hits")
        ok = len(results) > 0 and all(
            ix0 == romb(0x716B + ixt) and iy0 == romb(0x716B + iyt)
            for ixt, ix0, iyt, iy0 in results)
        sample = "; ".join(
            f"t{ixt}->{ix0}(exp{romb(0x716B+ixt)}) / t{iyt}->{iy0}(exp{romb(0x716B+iyt)})"
            for ixt, ix0, iyt, iy0 in results[:3])
        check("both parties remapped to transition_table[type]", ok, sample or "no samples")

        print("\n=== player_pos_snapshot (0x4C91): snapshot player Y/X + above-flag ===")
        # homing entities reach it; spawn dusters and capture at 0x4C9D (after both
        # copies): E129<-E301(player Y), E12A<-E302(player X)
        msx.cmd("debug break")
        msx.cmd("set ::ps 0; array unset ::py; array unset ::px; "
                "array unset ::e129; array unset ::e12a")
        bp = msx.cmd(
            "debug set_bp 0x4C9D true {"
            "set ::py($::ps) [debug read memory 0xE301]; "
            "set ::px($::ps) [debug read memory 0xE302]; "
            "set ::e129($::ps) [debug read memory 0xE129]; "
            "set ::e12a($::ps) [debug read memory 0xE12A]; incr ::ps}")
        msx.cont()
        for _ in range(4):
            game.spawn_type(0x0A, y=60, x=120)
            time.sleep(0.4)
        msx.cmd("debug break")
        ps = int(msx.cmd("set ::ps"))
        snaps = []
        for i in range(min(ps, 8)):
            snaps.append((int(msx.cmd(f"set ::py({i})")), int(msx.cmd(f"set ::px({i})")),
                          int(msx.cmd(f"set ::e129({i})")), int(msx.cmd(f"set ::e12a({i})"))))
        msx.cmd(f"debug remove_bp {bp}")
        ok = ps > 0 and all(e129 == py and e12a == px for py, px, e129, e12a in snaps)
        sample = "; ".join(f"Y{py}->E129={e129} X{px}->E12A={e12a}"
                           for py, px, e129, e12a in snaps[:3])
        check("player_pos_snapshot copies E301/E302 -> E129/E12A", ok, sample or "no hits")
        msx.cont()

    print(f"\n==== {len(PASS)} passed, {len(FAIL)} failed ====")
    if FAIL:
        print("FAILED:", ", ".join(FAIL)); sys.exit(1)


if __name__ == "__main__":
    main()
