"""Subsystem D — confirm the map-script command interpreter (sub_94c3).

Live-confirms, during real gameplay:
  1. The 13-entry command jump-table is actually driven: histogram of the
     command nibble (A & 0xf at the CALL 0x5c2e dispatch, PC=0x94e8).
  2. The script program-counter state advances:
        0xe702 = current scroll row (advanced per column)
        0xe704 = map-script program counter (ROM ptr, walks forward)
        0xe706 = next-command trigger row
  3. scroll_map_reader (0x9888) and scroll_vram_write (0x9a79) run each frame.
  4. The "ROUND n" banner command (cmd 8, handler 0x9699, print at 0x96bf)
     fires, and 0xe701 holds the round number.
"""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from zanackb.zanac_game import ZanacGame

CMD_TABLE = {  # from inline jump table at 0x94eb
    0: 0x97a8, 1: 0x97b3, 2: 0x9505, 3: 0x9537, 4: 0x956c, 5: 0x95a0,
    6: 0x9678, 7: 0x9680, 8: 0x9699, 9: 0x96de, 10: 0x96e5, 11: 0x9742,
    12: 0x977d,
}


def rd16(msx, addr):
    b = msx.read_memory(addr, 2)
    return b[0] | (b[1] << 8)


def main():
    with ZanacGame.launch("source/zanac.rom") as game:
        msx = game.client
        game.wait_for_title()
        game.start_game()
        time.sleep(1.5)

        # --- counters via non-breaking probes ---
        msx.cmd("set ::cmds {}")
        msx.cmd("set ::n_reader 0")
        msx.cmd("set ::n_vram 0")
        msx.cmd("set ::n_round 0")
        bps = [
            msx.set_breakpoint(0x94e8, "lappend ::cmds [reg A]"),
            msx.set_breakpoint(0x9888, "incr ::n_reader"),
            msx.set_breakpoint(0x9a79, "incr ::n_vram"),
            msx.set_breakpoint(0x96bf, "incr ::n_round"),
        ]

        # sample script PC while running
        msx.cont()
        pc_lo = rd16(msx, 0xe704)
        samples = []
        for _ in range(20):
            samples.append((rd16(msx, 0xe702), rd16(msx, 0xe704),
                            rd16(msx, 0xe706), msx.read_byte(0xe701)))
            time.sleep(0.3)
        pc_hi = rd16(msx, 0xe704)

        cmds_raw = msx.cmd("set ::cmds").split()
        n_reader = int(msx.cmd("set ::n_reader"))
        n_vram = int(msx.cmd("set ::n_vram"))
        n_round = int(msx.cmd("set ::n_round"))
        for bp in bps:
            msx.remove_breakpoint(bp)

        # ---- report ----
        print("=== command histogram (PC=0x94e8, A&0xf dispatched via 0x5c2e) ===")
        hist = {}
        for c in cmds_raw:
            v = int(c) & 0xf
            hist[v] = hist.get(v, 0) + 1
        for v in sorted(hist):
            tgt = CMD_TABLE.get(v, 0)
            print(f"  cmd {v:2d} -> 0x{tgt:04x}   x{hist[v]}")
        print(f"  total dispatches: {len(cmds_raw)}")

        print("\n=== script PC state (0xe702 row / 0xe704 PC / 0xe706 trigger / 0xe701 round) ===")
        for row, pc, trig, rnd in samples:
            print(f"  row={row:5d}  PC=0x{pc:04x}  trigger={trig:5d}  round={rnd}")
        print(f"  PC moved 0x{pc_lo:04x} -> 0x{pc_hi:04x} "
              f"(delta {pc_hi - pc_lo:+d})")

        print(f"\n=== per-frame routines ===")
        print(f"  scroll_map_reader (0x9888) hits: {n_reader}")
        print(f"  scroll_vram_write (0x9a79) hits: {n_vram}")
        print(f"  ROUND banner print (0x96bf) hits: {n_round}")


if __name__ == "__main__":
    main()
