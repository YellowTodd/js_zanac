"""Find who writes the ALC candidate bytes E13F/E140/E141 (and E142 ctx).

Set a write-watchpoint on each; capture PC of the writer while the player holds
fire. Report distinct writer PCs + the instruction context.
"""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from zanackb.zanac_game import ZanacGame

TARGETS = [0xE13F, 0xE140, 0xE141, 0xE142]


def find_writers(msx, addr, hold_fire_game, dwell=2.5):
    msx.cmd("set ::wpcs {}")
    wp = msx.cmd(
        f"debug set_watchpoint write_mem {addr} {{}} "
        f"{{lappend ::wpcs [reg PC]}}")
    msx.cont()
    time.sleep(dwell)
    msx.cmd("debug break")
    raw = msx.cmd("set ::wpcs")
    msx.remove_watchpoint(wp)
    pcs = {}
    for tok in raw.split():
        try:
            v = int(tok, 16) if tok.startswith("0x") else int(tok)
        except ValueError:
            continue
        pcs[v] = pcs.get(v, 0) + 1
    return pcs


def main():
    with ZanacGame.launch() as game:
        msx = game.client
        game.wait_for_title()
        game.start_game()
        time.sleep(2.0)
        game.shoot_shot()  # hold fire across the whole probe
        for addr in TARGETS:
            pcs = find_writers(msx, addr, game)
            print(f"\n{addr:04X} writers:")
            if not pcs:
                print("  (no writes during window)")
            for pc, n in sorted(pcs.items(), key=lambda kv: -kv[1]):
                print(f"  PC={pc:04X}  x{n}")
            msx.cont()
            time.sleep(0.3)
        game.release_shot()


if __name__ == "__main__":
    main()
