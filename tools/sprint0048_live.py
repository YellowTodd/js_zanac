#!/usr/bin/env python3
"""Sprint 0048 — Subsystem F live behaviour: ship movement, shooting, fire display.

  player_ship_update (0x7612) — steer changes E302(X)/E301(Y); shoot spawns a
                                type-2 shot into the E320 slot table.
  update_fire_display (0x7594) — writes "FIRE " + fire_num digit at 0x3a59 and the
                                 ammo count (E14D, 3-digit) at 0x3a7a.

Run: .venv/bin/python tools/sprint0048_live.py
"""
import sys, time, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "zanackb"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from zanackb.zanac_game import ZanacGame

PASS, FAIL = [], []
def check(name, cond, detail):
    (PASS if cond else FAIL).append(name)
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}: {detail}")
def reg(msx, n): return int(msx.cmd(f"reg {n}"))
def vram(msx, a, n): return bytes(msx.read_debuggable("VRAM", a, n))

def microexec(msx, entry, regs=None, timeout=2.0):
    TRAP, SP = 0xE7F0, 0xEFFE
    msx.cmd("debug break")
    msx.write_memory(SP, bytes([TRAP & 0xFF, TRAP >> 8])); msx.cmd(f"reg SP {SP}")
    for r, v in (regs or {}).items(): msx.cmd(f"reg {r} {v}")
    msx.cmd(f"reg PC {entry}")
    bp = msx.set_breakpoint(TRAP, "debug break"); msx.cont()
    t0 = time.time()
    while time.time() - t0 < timeout:
        if not msx.is_running() and reg(msx, "PC") == TRAP: break
        time.sleep(0.01)
    msx.remove_breakpoint(bp)


def main():
    with ZanacGame.launch("source/zanac.rom") as game:
        msx = game.client
        game.wait_for_title(); game.start_game(); time.sleep(1.0)
        game.make_invincible(); time.sleep(0.5)

        print("\n=== player_ship_update (0x7612): steering moves the ship ===")
        def xy(): return msx.read_byte(0xE302), msx.read_byte(0xE301)
        x0, y0 = xy()
        game.steer(right=True); time.sleep(0.6); game.steer(); time.sleep(0.2)
        x1, y1 = xy()
        check("steer right increases X (E302)", x1 > x0, f"X {x0}->{x1}")
        game.steer(left=True); time.sleep(0.6); game.steer(); time.sleep(0.2)
        x2, _ = xy()
        check("steer left decreases X (E302)", x2 < x1, f"X {x1}->{x2}")
        _, ya = xy()
        game.steer(up=True); time.sleep(0.6); game.steer(); time.sleep(0.2)
        _, yb = xy()
        check("steer up decreases Y (E301)", yb < ya, f"Y {ya}->{yb}")

        print("\n=== player_ship_update: shoot spawns a type-2 shot slot ===")
        # breakpoint the shot-spawn write (0x76d9 = LD (HL),0x02) while holding fire
        msx.cmd("set ::shot 0")
        bp = msx.set_breakpoint(0x76D9, "incr ::shot")
        game.shoot_shot(); time.sleep(0.8); game.steer()
        hits = int(msx.cmd("set ::shot"))
        msx.remove_breakpoint(bp)
        check("shooting reaches shot-spawn write (0x76D9)", hits >= 1, f"hits={hits}")

        print("\n=== update_fire_display (0x7594): FIRE label + num + ammo ===")
        msx.write_byte(0xE14B, 3)         # fire_num = 3
        msx.write_byte(0xE14D, 0x40)      # ammo = 64
        microexec(msx, 0x7594)
        label = vram(msx, 0x3A59, 5); digit = vram(msx, 0x3A5E, 1)
        ammo = vram(msx, 0x3A7A, 3)
        check("'FIRE ' label at 0x3A59", label == b"FIRE ", f"{label!r}")
        check("fire_num digit '3' at 0x3A5E", digit == b"3", f"{digit!r}")
        check("ammo ' 64' (E14D=0x40, leading-zero blank) at 0x3A7A", ammo == b" 64", f"{ammo!r}")

    print(f"\n==== {len(PASS)} passed, {len(FAIL)} failed ====")
    if FAIL:
        print("FAILED:", ", ".join(FAIL)); sys.exit(1)


if __name__ == "__main__":
    main()
