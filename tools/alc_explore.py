"""Subsystem I (ALC) exploration — find the difficulty variable.

Capture the 0xE100..0xE1FF state page as a time-series under two play styles:
  IDLE     : no fire, no movement
  SHOOTING : hold SPACE (shot+fire) continuously

ALC is performance-driven, so its byte should climb under SHOOTING much faster
than under IDLE, while ordinary timers/counters climb the same in both.
"""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from zanackb.zanac_game import ZanacGame, MSXKey

LO, HI = 0xE100, 0xE200
N = LO  # base


def snap(msx):
    return list(msx.read_memory(LO, HI - LO))


def trajectory(msx, samples=12, dt=0.25):
    rows = []
    for _ in range(samples):
        rows.append(snap(msx))
        time.sleep(dt)
    return rows


def summarize(rows):
    """per-offset (first, last, min, max, monotone-up?)"""
    out = {}
    width = len(rows[0])
    for i in range(width):
        col = [r[i] for r in rows]
        mono = all(b >= a for a, b in zip(col, col[1:]))
        out[i] = (col[0], col[-1], min(col), max(col), mono, col)
    return out


def main():
    with ZanacGame.launch() as game:
        msx = game.client
        game.wait_for_title()
        game.start_game()
        time.sleep(2.0)  # settle into gameplay

        # ---- IDLE window (no keys) ----
        idle = trajectory(msx)

        # ---- SHOOTING window (hold SHIFT = normal shot, continuous) ----
        game.shoot_shot()  # key_down SHIFT, stays held
        shoot_rows = []
        for _ in range(12):
            shoot_rows.append(snap(msx))
            time.sleep(0.25)
        game.release_shot()

        si = summarize(idle)
        ss = summarize(shoot_rows)

        print("offset addr  idle(f->l,rng)      shoot(f->l,rng)   delta_shoot-idle")
        for i in range(len(idle[0])):
            f_i, l_i, mn_i, mx_i, mo_i, _ = si[i]
            f_s, l_s, mn_s, mx_s, mo_s, _ = ss[i]
            d_idle = l_i - f_i
            d_shoot = l_s - f_s
            # only show bytes that move, and where shooting moves them more
            if (mx_i != mn_i or mx_s != mn_s):
                flag = ""
                if d_shoot > d_idle + 1:
                    flag = "  <== climbs more under fire"
                print(f"+{i:02X}   {LO+i:04X}  {f_i:3d}->{l_i:3d} [{mn_i:3d},{mx_i:3d}]   "
                      f"{f_s:3d}->{l_s:3d} [{mn_s:3d},{mx_s:3d}]  {d_shoot-d_idle:+4d}{flag}")


if __name__ == "__main__":
    main()
