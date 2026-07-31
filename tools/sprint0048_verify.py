#!/usr/bin/env python3
"""Sprint 0048 — Subsystem F (player ship & weapons): confirm weapon engine.

Micro-exec (pause CPU, plant inputs, hijack PC, trap on stack sentinel or a known
exit address, read back results):

  set_velocity_from_dir (0x4cf7)  — dir -> IX+8/9 (Xv), IX+a/b (Yv) via vel_dir_table
  fire switcher        (0x7548)   — fire_num -> E14D/E14E from fire_init_table (0x751f)
  load_shot_params     (0x7771)   — shot_level -> E10E/E10D/E10F from shot_power_table (0x778f)
  fire dispatch        (0x5c2e)   — fire_num -> handler via inline tables
                                     init 0x7269, update 0x727f, expire 0x74ae

Run: .venv/bin/python tools/sprint0048_verify.py
"""
import sys, time, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "zanackb"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from zanackb.zanac_game import ZanacGame

ROM = open(pathlib.Path(__file__).resolve().parent.parent / "source/zanac.rom", "rb").read()
def romb(a): return ROM[a - 0x4000]
def romw(a): return romb(a) | (romb(a + 1) << 8)

TRAP, SP = 0xE7F0, 0xEFFE
SCRATCH = 0xE7A0                 # scratch "entity" for IX-based routines
PASS, FAIL = [], []
def check(name, cond, detail):
    (PASS if cond else FAIL).append(name)
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}: {detail}")
def reg(msx, n, v=None):
    if v is None: return int(msx.cmd(f"reg {n}"))
    msx.cmd(f"reg {n} {v}")

def s16(v): return v - 0x10000 if v >= 0x8000 else v

def microexec(msx, entry, regs=None, exit_addr=None, timeout=2.0):
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
    return reg(msx, "PC")

def dispatch_target(msx, entry, fire_num, candidates):
    """Set fire_num, run from `entry` (which does CALL 0x5c2e <inline table>),
    break at whichever candidate handler address is reached first; return it."""
    msx.cmd("debug break")
    msx.write_byte(0xE14B, fire_num)
    msx.write_memory(SP, bytes([TRAP & 0xFF, TRAP >> 8])); reg(msx, "SP", SP)
    reg(msx, "PC", entry)
    bps = [msx.set_breakpoint(a, "debug break") for a in set(candidates)]
    msx.cont()
    t0 = time.time(); pc = None
    while time.time() - t0 < 2.0:
        if not msx.is_running():
            pc = reg(msx, "PC"); break
        time.sleep(0.01)
    for b in bps: msx.remove_breakpoint(b)
    return pc


def main():
    with ZanacGame.launch("source/zanac.rom") as game:
        msx = game.client
        game.wait_for_title(); game.start_game(); time.sleep(1.0)
        game.make_invincible(); time.sleep(0.3)

        # ---- set_velocity_from_dir (0x4cf7) ----
        print("\n=== set_velocity_from_dir (0x4cf7): dir -> IX+8/9 (Xv), IX+a/b (Yv) ===")
        for d in (0, 4, 8, 12, 2, 6):
            msx.write_byte(SCRATCH + 0x17, 0x01)          # speed = 1, no bit6/7 scaling
            microexec(msx, 0x4cf7, {"E": d, "IX": SCRATCH})
            xv = s16(msx.read_byte(SCRATCH + 8) | (msx.read_byte(SCRATCH + 9) << 8))
            yv = s16(msx.read_byte(SCRATCH + 0xa) | (msx.read_byte(SCRATCH + 0xb) << 8))
            exp_x = s16(romw(0x4d65 + d * 4)); exp_y = s16(romw(0x4d65 + d * 4 + 2))
            check(f"dir {d:2d} -> ({xv:+d},{yv:+d})", (xv, yv) == (exp_x, exp_y),
                  f"got ({xv:+d},{yv:+d}) exp ({exp_x:+d},{exp_y:+d})")

        # ---- fire switcher (0x7548) -> fire_init_table (0x751f) ----
        print("\n=== fire switcher (0x7548): fire_num -> E14D/E14E from 0x751f ===")
        for n in range(8):
            microexec(msx, 0x7548, {"A": n}, exit_addr=0x7564)
            e14d = msx.read_byte(0xE14D); e14e = msx.read_byte(0xE14E)
            e14b = msx.read_byte(0xE14B); e14c = msx.read_byte(0xE14C)
            exp_d = romb(0x751f + n * 2); exp_e = romb(0x751f + n * 2 + 1)
            ok = e14d == exp_d and e14e == exp_e and e14b == n and e14c == 0x3c
            check(f"fire {n}: E14B={e14b} E14C={e14c:02x} E14D={e14d:02x} E14E={e14e:02x}",
                  ok, f"exp E14D={exp_d:02x} E14E={exp_e:02x} E14B={n} E14C=3c")

        # ---- load_shot_params (0x7771) -> shot_power_table (0x778f) ----
        print("\n=== load_shot_params (0x7771): shot_level -> E10E/E10D/E10F from 0x778f ===")
        for lvl in range(6):
            msx.write_byte(0xE10B, lvl)
            microexec(msx, 0x7771)
            vy = msx.read_byte(0xE10E); cap = msx.read_byte(0xE10D); name = msx.read_byte(0xE10F)
            exp = [romb(0x778f + lvl * 3 + k) for k in range(3)]
            ok = [vy, cap, name] == exp
            check(f"shot lvl {lvl}: vy={vy:02x} cap={cap:02x} name={name:02x}",
                  ok, f"exp {[f'{x:02x}' for x in exp]}")

        # ---- fire dispatch via 0x5c2e (init/update/expire tables) ----
        print("\n=== fire dispatch (0x5c2e): fire_num -> handler ===")
        init  = [romw(0x7269 + n * 2) for n in range(8)]
        upd   = [romw(0x727f + n * 2) for n in range(8)]
        expi  = [romw(0x74ae + n * 2) for n in range(8)]
        for label, entry, tbl in (("init 0x7269", 0x7263, init),
                                   ("update 0x727f", 0x7279, upd),
                                   ("expire 0x74ae", 0x74a8, expi)):
            for n in (0, 3, 4, 7):
                pc = dispatch_target(msx, entry, n, tbl)
                check(f"{label} fire {n} -> 0x{tbl[n]:04x}", pc == tbl[n],
                      f"landed 0x{pc:04x}" if pc else "no hit")

    print(f"\n==== {len(PASS)} passed, {len(FAIL)} failed ====")
    if FAIL:
        print("FAILED:", ", ".join(FAIL)); sys.exit(1)


if __name__ == "__main__":
    main()
