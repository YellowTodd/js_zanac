"""
Sprint 0033 — Compare full RAM state: game-end save state vs round-1 start.
Both captures happen right when the game enters the credits / main game loop.
"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from zanackb.openmsx import OpenMsxClient
from zanackb.zanac_game import ZanacGame

ROM = "source/zanac.rom"
IPS = "scripts/invincible.ips"
SAVESTATE = "savestates/game-end.oms"


def snapshot(msx, label):
    """Capture all credits-relevant state."""
    snap = {}
    for addr in range(0xE700, 0xE724):
        snap[addr] = msx.read_byte(addr)
    # Sound channel slot 0 first 4 bytes
    snap["snd0_flags"] = msx.read_byte(0xE20C)
    snap["snd0_event"] = msx.read_byte(0xE20D)
    snap["snd0_b"]     = msx.read_byte(0xE20E)
    snap["snd0_c"]     = msx.read_byte(0xE20F)
    # E102
    snap["e102"] = msx.read_byte(0xE102)
    # Level stream 16-bit
    snap["e704_16"] = msx.read_byte(0xE704) | (msx.read_byte(0xE705) << 8)
    snap["e722_16"] = msx.read_byte(0xE722) | (msx.read_byte(0xE723) << 8)
    return snap


def boot_savestate():
    client, proc = OpenMsxClient.connect_subprocess(
        rom=ROM, extra_args=("-ips", IPS, "-savestate", SAVESTATE), timeout=30.0
    )
    game = ZanacGame(client, proc)
    msx  = client
    msx.cmd("set ::cold 0")
    bp = msx.set_breakpoint(0x4010, "set ::cold 1")
    msx.power_on()
    msx.poll_flag("cold", interval=0.3, timeout=15.0)
    msx.remove_breakpoint(bp)
    # Wait 0.5 s for game to settle into credits loop
    msx.cont()
    time.sleep(0.5)
    snap = snapshot(msx, "game-end")
    game.cleanup(); proc.terminate(); proc.wait()
    return snap


def boot_round1():
    client, proc = OpenMsxClient.connect_subprocess(rom=ROM, timeout=20.0)
    game = ZanacGame(client, proc)
    msx  = client
    msx.cmd("set ::cold 0")
    bp = msx.set_breakpoint(0x4010, "set ::cold 1")
    msx.power_on()
    msx.poll_flag("cold", interval=0.3, timeout=12.0)
    msx.remove_breakpoint(bp)
    game.wait_for_title()
    game.start_game()
    time.sleep(0.5)   # settle in round-1 main loop
    snap = snapshot(msx, "round-1")
    game.cleanup(); proc.terminate(); proc.wait()
    return snap


def main():
    print("Capturing game-end state...")
    end = boot_savestate()
    print("Capturing round-1 baseline...")
    r1  = boot_round1()

    # Print comparison of all E700-E723 registers
    print(f"\n{'Addr':>6}  {'Name':16}  {'Round-1':>8}  {'Game-end':>8}  Diff")
    print(f"{'─'*6}  {'─'*16}  {'─'*8}  {'─'*8}  {'─'*30}")

    names = {
        0xE700: "scroll_flags",
        0xE701: "stage",
        0xE702: "row_ctr",
        0xE704: "stream_ptr_lo",
        0xE705: "stream_ptr_hi",
        0xE706: "stream_val_lo",
        0xE707: "stream_val_hi",
        0xE710: "scroll_spd",
        0xE711: "scroll_acc",
        0xE712: "target_spd",
        0xE713: "vel_timer",
        0xE714: "scroll_row",
        0xE722: "e722_lo",
        0xE723: "e722_hi",
    }

    for addr in range(0xE700, 0xE724):
        v1 = r1.get(addr, 0)
        ve = end.get(addr, 0)
        name = names.get(addr, "")
        diff = f"*** {ve-v1:+d}" if v1 != ve else ""
        if v1 != ve or name:
            print(f"0x{addr:04X}  {name:16}  0x{v1:02X}       0x{ve:02X}       {diff}")

    # E102
    print()
    v1, ve = r1["e102"], end["e102"]
    print(f"0xE102   {'e102':16}  0x{v1:02X}       0x{ve:02X}       {'*** changed' if v1!=ve else ''}")
    print(f"         {'stream_ptr':16}  0x{r1['e704_16']:04X}     0x{end['e704_16']:04X}")
    print(f"         {'e722':16}  0x{r1['e722_16']:04X}     0x{end['e722_16']:04X}")

    # Sound
    print()
    print("Sound channel 0 (0xE20C):")
    print(f"  Round-1:  flags=0x{r1['snd0_flags']:02X}  event=0x{r1['snd0_event']:02X}  b=0x{r1['snd0_b']:02X}  c=0x{r1['snd0_c']:02X}")
    print(f"  Game-end: flags=0x{end['snd0_flags']:02X}  event=0x{end['snd0_event']:02X}  b=0x{end['snd0_b']:02X}  c=0x{end['snd0_c']:02X}")

    print()
    print("=== Key differences to replicate in credits.tcl ===")
    diffs = {addr: (r1[addr], end[addr]) for addr in range(0xE700, 0xE724)
             if r1.get(addr) != end.get(addr)}
    for addr, (v_r1, v_end) in sorted(diffs.items()):
        print(f"  E{addr-0xE000:03X}: round1=0x{v_r1:02X}  credits=0x{v_end:02X}  ({names.get(addr,'')})")


if __name__ == "__main__":
    main()
