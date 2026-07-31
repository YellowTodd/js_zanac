"""Compare the initial ALC / difficulty state across rounds 1-8 and secret 0.

Warp to each round (scripts/warp.tcl), start, settle without input, then read:
  - the on-screen ALC bytes  E12E / E132 / E130  (the "ALC" HUD readout)
  - spawn pacing  E138 (spawn_timer_reload), E136 (spawn_subtable_max)
  - peak on-screen enemies over a short idle window
"""
import sys, os, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from zanackb.openmsx import OpenMsxClient
from zanackb.zanac_game import ZanacGame

ROM, WARP = "source/zanac.rom", "scripts/warp.tcl"


def enemies(msx):
    return sum(1 for a in range(0xE320, 0xE640, 0x20) if msx.read_byte(a))


def probe(round_num, tcl):
    client, proc = OpenMsxClient.connect_subprocess(rom=ROM, timeout=20.0)
    game = ZanacGame(client, proc)
    msx = client
    try:
        msx.cmd("set ::zanac_cold_start 0")
        bp = msx.set_breakpoint(0x4010, "set ::zanac_cold_start 1")
        msx.power_on()
        msx.poll_flag("zanac_cold_start", interval=0.3, timeout=12.0)
        msx.remove_breakpoint(bp)
        game.wait_for_title()
        msx.cmd(tcl)
        msx.cmd(f"warp {round_num}")
        game.fire_shot(duration=0.15)   # SPACE-equivalent start
        time.sleep(2.0)                 # settle into gameplay
        # idle window: average + peak live enemies (difficulty signal)
        samples, peak = [], 0
        for _ in range(60):             # ~6s
            n = enemies(msx)
            samples.append(n); peak = max(peak, n)
            time.sleep(0.1)
        avg = sum(samples) / len(samples)
        rd = msx.read_byte(0xE701)
        e12e, e132, e130 = (msx.read_byte(0xE12E), msx.read_byte(0xE132),
                            msx.read_byte(0xE130))
        e138, e136 = msx.read_byte(0xE138), msx.read_byte(0xE136)
        return rd, e12e, e132, e130, e138, e136, avg, peak
    finally:
        game.cleanup()
        proc.terminate(); proc.wait()


def main():
    with open(WARP) as f:
        tcl = f.read()
    print("warp  E701  ALC(E12E E132 E130)  reload(E138)  submax(E136)  avg_enemies  peak")
    for r in [1, 2, 3, 4, 5, 6, 7, 8, 0]:
        rd, a, b, c, e138, e136, avg, peak = probe(r, tcl)
        print(f"  {r}    {rd:#04x}    {a:02x} {b:02x} {c:02x}            "
              f"{e138:#04x}         {e136:#04x}         {avg:4.1f}        {peak}")


if __name__ == "__main__":
    main()
