"""
Sprint 0033 — Trace PC / E102 / E700 / E701 / E712 frame by frame from
the game-end save state, and compare with normal round-1 play.

Samples every main-loop entry (LAB_4074) for 300 frames to show how
the state machine transitions from final-boss-defeat → wipe → music →
credits, including which branches are taken and what E102 bits drive them.
"""

import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from zanackb.openmsx import OpenMsxClient
from zanackb.zanac_game import ZanacGame

ROM       = "source/zanac.rom"
IPS       = "scripts/invincible.ips"
SAVESTATE = "savestates/game-end.oms"

MAIN_LOOP = 0x4074   # LAB_4074

# E102 branch targets in the main loop
BRANCHES = {
    0x40DA: "level_complete(bit5)",
    0x46D5: "credits(bit3)",
    0x4042: "title(bit7)",
    0x41BA: "display_timer(bit4)",
}


def trace_run(label, extra_args, max_frames=300, stop_at=None):
    """Boot (with optional save state), sample state at each main-loop entry."""
    print(f"\n{'═'*70}")
    print(f"  TRACE: {label}")
    print(f"{'═'*70}")
    print(f"  {'Frame':>5}  {'E102':>6}  {'E700':>6}  {'E701':>6}  {'E712':>6}  "
          f"{'stream':>8}  Branch / note")
    print(f"  {'─'*5}  {'─'*6}  {'─'*6}  {'─'*6}  {'─'*6}  {'─'*8}  {'─'*30}")

    client, proc = OpenMsxClient.connect_subprocess(
        rom=ROM, extra_args=extra_args, timeout=30.0
    )
    game = ZanacGame(client, proc)
    msx  = client
    try:
        msx.cmd("set ::cold 0")
        bp = msx.set_breakpoint(0x4010, "set ::cold 1")
        msx.power_on()
        msx.poll_flag("cold", interval=0.3, timeout=15.0)
        msx.remove_breakpoint(bp)

        if stop_at is None:
            # Wait for title then start game for round-1 baseline
            game.wait_for_title()
            game.start_game()
            time.sleep(0.3)

        # Install a per-frame counter breakpoint at main loop
        msx.cmd("set ::frame_n 0; set ::snap {}")
        msx.cmd("""
            proc snap_frame {} {
                set n [incr ::frame_n]
                set e102 [debug read memory 0xe102]
                set e700 [debug read memory 0xe700]
                set e701 [debug read memory 0xe701]
                set e712 [debug read memory 0xe712]
                set slo  [debug read memory 0xe704]
                set shi  [debug read memory 0xe705]
                set sptr [expr {$slo | ($shi << 8)}]
                lappend ::snap [list $n $e102 $e700 $e701 $e712 $sptr]
            }
        """)
        bp_main = msx.set_breakpoint(MAIN_LOOP, "snap_frame")

        # Also watch branch addresses
        for addr, note in BRANCHES.items():
            msx.cmd(f"set ::br_{addr:04x} 0")
            msx.set_breakpoint(addr,
                f"incr ::br_{addr:04x}; "
                f"lappend ::snap [list $::frame_n {addr} caught]")

        msx.cont()
        time.sleep(max_frames / 60.0 + 1.0)
        msx.remove_breakpoint(bp_main)

        # Fetch the snapshot list
        raw = msx.cmd("set ::snap")
        frames = []
        for item in raw.split("{"):
            item = item.strip().rstrip("}")
            if not item:
                continue
            parts = item.split()
            if len(parts) >= 3 and parts[2] == "caught":
                frames.append(("BRANCH", int(parts[0]), int(parts[1], 16)))
            elif len(parts) == 6:
                n, e102, e700, e701, e712, sptr = parts
                frames.append(("FRAME", int(n), int(e102), int(e700),
                                int(e701), int(e712), int(sptr)))

        prev_e102 = None
        for f in frames:
            if f[0] == "BRANCH":
                _, frame_n, addr = f
                note = BRANCHES.get(addr, f"0x{addr:04X}")
                print(f"  {'':>5}  {'':>6}  {'':>6}  {'':>6}  {'':>6}  "
                      f"{'':>8}  *** BRANCH → {note}")
            else:
                _, n, e102, e700, e701, e712, sptr = f
                changed = e102 != prev_e102
                note = f"E102 changed: 0x{prev_e102:02X}→0x{e102:02X}" if changed and prev_e102 is not None else ""
                print(f"  {n:>5}  0x{e102:02X}    0x{e700:02X}    0x{e701:02X}    "
                      f"0x{e712:02X}    0x{sptr:04X}    {note}")
                prev_e102 = e102
            if len(frames) > 20 and f[0] == "FRAME" and f[2] == prev_e102:
                pass  # deduplicate steady-state runs

    finally:
        game.cleanup(); proc.terminate(); proc.wait()


def main():
    # ── 1. Save-state trace (game-end → credits) ─────────────────────────────
    trace_run(
        "GAME END save state → credits sequence",
        extra_args=("-ips", IPS, "-savestate", SAVESTATE),
        max_frames=600,
    )

    # ── 2. Round-1 baseline ───────────────────────────────────────────────────
    trace_run(
        "Round 1 normal play (baseline)",
        extra_args=(),
        max_frames=120,
        stop_at="game",
    )


if __name__ == "__main__":
    main()
