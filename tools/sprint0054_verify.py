"""Sprint 0054 — Subsystem H (items & pickups) verification.

Micro-exec in openMSX:
  1. jump-table: type 63 → handler 0x78AF.
  2. box drop: drive the box death branch 0x7878 with +0x18 = 4/5/6 and read the
     resulting entity type (38 bullets / nothing / 63 chip).
  3. power-chip apply: run 0x78D7 with shot_level=3, confirm it becomes 4 and the
     shot params reload.
"""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from zanackb.zanac_game import ZanacGame

SLOT = 0xE3A0


def reg(msx, name, val=None):
    if val is None:
        return int(msx.cmd(f"reg {name}"))
    msx.cmd(f"reg {name} {val}")


def step_until_type_change(msx, start_pc, ix, base_type, lo=0x7878, hi=0x78a0, maxn=14):
    reg(msx, "ix", ix)
    reg(msx, "pc", start_pc)
    for _ in range(maxn):
        msx.cmd("step")
        pc = reg(msx, "pc")
        t = msx.read_byte(SLOT)
        if t != base_type or not (lo <= pc <= hi):
            return t
    return msx.read_byte(SLOT)


def main():
    p, f = [], []
    with ZanacGame.launch() as game:
        msx = game.client
        game.wait_for_title(); game.start_game(); time.sleep(1.2)
        msx.cmd("debug break")   # halt CPU so reg/step micro-exec is deterministic

        # 1. jump table: type 63 → 0x78AF
        jt = bytes(msx.read_memory(0x70B7 + 63 * 2, 2))
        ent = jt[0] | (jt[1] << 8)
        print(f"jump_table[63] = 0x{ent:04X}")
        (p if ent == 0x78AF else f).append(f"type63 handler = 0x{ent:04X} (want 0x78AF)")

        # 2. box drop branch (0x7878): +0x18 = 4 / 5 / 6
        BOX = 0x84  # box active type
        for plus18, want, label in [(0x04, 0x26, "bullets→type38"),
                                    (0x05, 0x84, "nothing→unchanged"),
                                    (0x06, 0xBF, "chip→type63")]:
            msx.write_memory(SLOT, bytes(32))
            msx.write_byte(SLOT, BOX)
            msx.write_byte(SLOT + 0x18, plus18)
            got = step_until_type_change(msx, 0x7878, SLOT, BOX)
            ok = got == want
            print(f"box +0x18={plus18:#04x}: type→0x{got:02X} ({label})  {'OK' if ok else 'FAIL'}")
            (p if ok else f).append(f"box drop +0x18={plus18:#04x} → 0x{got:02X}")

        # 3. power-chip apply (0x78D7): shot_level 3 → 4 + params reload
        msx.write_byte(0xE10B, 0x03)
        before = bytes(msx.read_memory(0xE10D, 3))  # cap, vy, sat
        reg(msx, "pc", 0x78D7)
        lvl = None
        for _ in range(60):                 # step through store + load_shot_params
            msx.cmd("step")
            if lvl is None and msx.read_byte(0xE10B) == 4:
                lvl = 4
            if msx.read_byte(0xE10D) != before[0]:
                break
        lvl = lvl or msx.read_byte(0xE10B)
        after = bytes(msx.read_memory(0xE10D, 3))
        print(f"power chip: shot_level 3→{lvl}; params {before.hex()}→{after.hex()}")
        (p if lvl == 4 else f).append(f"power chip shot_level→{lvl} (want 4)")
        (p if after != before else f).append("power chip reloaded shot params")

        # 4. fire-weapon grant: black-shadow death tail 0x8EA9 → fire_select(+0x1c)
        msx.write_memory(SLOT, bytes(32))
        msx.write_byte(SLOT + 0x1c, 0x05)   # weapon number 5
        reg(msx, "ix", SLOT)
        reg(msx, "pc", 0x8EA9)              # LD A,(IX+0x1c)
        msx.cmd("step")                      # A = 5
        msx.cmd("step")                      # JP 0x7548
        a = reg(msx, "af") >> 8
        pc = reg(msx, "pc")
        print(f"fire grant: A=0x{a:02X} PC=0x{pc:04X} (want A=5, PC=0x7548)")
        (p if a == 5 and pc == 0x7548 else f).append("black-shadow → fire_select(+0x1c)")

    print("\n=== RESULTS ===")
    for x in p: print("  PASS", x)
    for x in f: print("  FAIL", x)
    print(f"\n{len(p)} passed, {len(f)} failed")
    return 1 if f else 0


if __name__ == "__main__":
    sys.exit(main())
