"""Why is round 0 more aggressive? Spawn RATE is ~equal across rounds; characterise
the live-entity population by type instead (harder enemies fire more bullets).

Clean idle window (no breakpoints), sample the entity table, tally types.
"""
import sys, time
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from zanackb.zanac_game import ZanacGame

# rough taxonomy from subsystem G
BULLET_TYPES = {0x25, 0x26, 0x27, 0x35, 0x37, 0x42, 0x43, 0x24}  # projectiles/bullets


def probe(round_num, secs=8.0):
    with ZanacGame.launch() as game:
        msx = game.client
        game.wait_for_title()
        game.arm_warp(round_num)
        game.start_game()
        time.sleep(2.0)
        types = Counter()
        peak = 0
        samples = 0
        t_end = time.time() + secs
        while time.time() < t_end:
            live = 0
            for a in range(0xE320, 0xE640, 0x20):
                t = msx.read_byte(a) & 0x7f
                if t:
                    types[t] += 1
                    live += 1
            peak = max(peak, live)
            samples += 1
            time.sleep(0.12)
        e701 = msx.read_byte(0xE701)
    return e701, types, peak, samples


def main():
    for r in (1, 0):
        e701, types, peak, samples = probe(r)
        tot = sum(types.values())
        bullets = sum(n for t, n in types.items() if t in BULLET_TYPES)
        avg = tot / samples
        print(f"\n=== warp {r}  E701={e701:#04x}  samples={samples} ===")
        print(f"  avg live entities/frame = {avg:4.1f}   peak = {peak}")
        print(f"  bullet/projectile share  = {bullets}/{tot} = {bullets/max(tot,1)*100:4.0f}%")
        print(f"  type histogram (type: avg present): ")
        for t, n in types.most_common(14):
            print(f"    {t:#04x}: {n/samples:4.1f}")


if __name__ == "__main__":
    main()
