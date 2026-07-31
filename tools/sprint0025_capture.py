#!/usr/bin/env python3
"""Sprint 0025 — Airborne enemy cluster live capture.

Runs the game for ~60 dispatch breaks (≈180 dispatches ≈ 3 min game time),
collects entity slot snapshots for types 4–37, and prints a per-type summary.
"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools" / "zanackb"))

from zanac_game import ZanacGame, MSXKey  # noqa: E402

ROM = ROOT / "source" / "zanac.rom"


def decode_slot(slot: bytes) -> dict:
    typ      = slot[0x00] & 0x7F
    active   = bool(slot[0x00] & 0x80)
    y        = slot[0x01]
    x        = slot[0x02]
    sat_name = slot[0x03]
    sat_col  = slot[0x04]
    flags    = slot[0x05]
    vy_frac  = slot[0x08]
    vy       = slot[0x09]
    vx_frac  = slot[0x0A]
    vx       = slot[0x0B]
    bflags   = slot[0x0C]
    anim_tick= slot[0x0D]
    anim_rate= slot[0x0E]
    anim_fr  = slot[0x0F]
    anim_max = slot[0x10]
    anim_lo  = slot[0x11]
    anim_hi  = slot[0x12]
    tgt_y    = slot[0x13]
    tgt_x    = slot[0x14]
    y_acc    = slot[0x15]
    x_acc    = slot[0x16]
    h_iters  = slot[0x17]
    col_type = slot[0x18]
    pers19   = slot[0x19]
    child_lo = slot[0x1B]
    child_hi = slot[0x1C]
    col_wid  = slot[0x1D]
    pers1e   = slot[0x1E]
    return dict(
        typ=typ, active=active, y=y, x=x,
        sat_name=sat_name, sat_col=sat_col, flags=flags,
        vy=vy, vy_frac=vy_frac, vx=vx, vx_frac=vx_frac,
        bflags=bflags,
        anim_tick=anim_tick, anim_rate=anim_rate,
        anim_fr=anim_fr, anim_max=anim_max,
        anim_lo=anim_lo, anim_hi=anim_hi,
        tgt_y=tgt_y, tgt_x=tgt_x, y_acc=y_acc, x_acc=x_acc,
        h_iters=h_iters, col_type=col_type, pers19=pers19,
        child_lo=child_lo, child_hi=child_hi,
        col_wid=col_wid, pers1e=pers1e,
    )


def main():
    seen: dict[int, list[dict]] = {}

    with ZanacGame.launch(str(ROM)) as game:
        msx = game.client
        game.wait_for_title()
        game.start_game()
        game.steer(up=True)
        time.sleep(1.0)

        # Short initial settle, then grant permanent invincibility
        time.sleep(2.0)
        # Player slot at 0xE300: set +0x05 bit7=1 (invincible), +0x1B=0xFF (timer)
        msx.write_byte(0xE305, msx.read_byte(0xE305) | 0x80)
        msx.write_byte(0xE31B, 0xFF)

        msx.cmd("set ::n 0")
        bp = msx.set_breakpoint(
            0x445F,
            "incr ::n; if {$::n % 30 == 0} {debug break}",  # every 30 frames ≈ 0.6s
        )

        for iteration in range(120):           # 120 × 30 frames ≈ 72 s game time
            msx.cont()
            time.sleep(0.7)                    # headroom for 30 frames at 50 FPS
            # Refresh invincibility so the timer never hits 0
            msx.write_byte(0xE305, msx.read_byte(0xE305) | 0x80)
            msx.write_byte(0xE31B, 0xFF)
            raw = bytes(msx.read_memory(0xE300, 26 * 32))
            if iteration % 20 == 0:
                active = sum(1 for i in range(26) if raw[i*32] & 0x80)
                types_seen = sorted({raw[i*32] & 0x7F for i in range(26) if raw[i*32] & 0x80})
                print(f"  iter {iteration:3d}: {active} active, types: {types_seen}", flush=True)
            for i in range(26):
                slot = raw[i * 32 : (i + 1) * 32]
                s = decode_slot(slot)
                typ = s["typ"]
                if 4 <= typ <= 37 and typ not in (11, 35):
                    seen.setdefault(typ, []).append(s)

        msx.remove_breakpoint(bp)

    # ── Report ────────────────────────────────────────────────────────────────
    print("\n=== Sprint 0025 — Entity slot summary ===\n")
    for typ in sorted(seen):
        samples = seen[typ]
        n = len(samples)

        # Most common sat_name and sat_col
        sat_names = [s["sat_name"] for s in samples]
        sat_cols  = [s["sat_col"]  for s in samples]
        bflags    = [s["bflags"]   for s in samples]
        vys       = [s["vy"]       for s in samples]
        vxs       = [s["vx"]       for s in samples]
        child_ptrs= [(s["child_hi"] << 8) | s["child_lo"] for s in samples]
        col_wids  = [s["col_wid"]  for s in samples]
        pers19s   = [s["pers19"]   for s in samples]
        pers1es   = [s["pers1e"]   for s in samples]
        anim_tabs = [(s["anim_hi"] << 8) | s["anim_lo"] for s in samples]

        def mode(lst):
            return max(set(lst), key=lst.count)

        def pct_nonzero(lst):
            return 100 * sum(1 for v in lst if v) // len(lst)

        sat_name_m = mode(sat_names)
        pat = sat_name_m >> 2
        sat_col_m  = mode(sat_cols)
        bflag_m    = mode(bflags)
        vy_m       = mode(vys)
        vx_m       = mode(vxs)
        child_m    = mode(child_ptrs)
        anim_m     = mode(anim_tabs)

        print(f"Type {typ:2d}  (n={n:3d})")
        print(f"  sat_name 0x{sat_name_m:02X} → pattern {pat}")
        print(f"  sat_col  0x{sat_col_m:02X}")
        print(f"  bflags   0x{bflag_m:02X}  (Y:{bflag_m&1} X:{(bflag_m>>1)&1}"
              f" anim:{(bflag_m>>2)&1} Yhom:{(bflag_m>>3)&1} Xhom:{(bflag_m>>4)&1})")
        print(f"  vy mode  0x{vy_m:02X} ({vy_m})  vx mode 0x{vx_m:02X} ({vx_m})")
        if child_m:
            print(f"  child_ptr 0x{child_m:04X}  col_wid mode {mode(col_wids)}")
        if anim_m:
            print(f"  anim_table 0x{anim_m:04X}  anim_max mode {mode([s['anim_max'] for s in samples])}")
        if any(p != 0 for p in pers19s):
            print(f"  +0x19 mode {mode(pers19s)}")
        if any(p != 0 for p in pers1es):
            print(f"  +0x1E mode {mode(pers1es)}")
        # Show all unique sat_names seen (animation cycling)
        unique_names = sorted(set(sat_names))
        if len(unique_names) > 1:
            print(f"  sat_names seen: {[hex(v) for v in unique_names]}")
        print()


if __name__ == "__main__":
    main()
