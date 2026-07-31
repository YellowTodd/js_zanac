"""Test scripts/credits.tcl — check all 5 sound channels + verify trampoline fired."""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from zanackb.openmsx import OpenMsxClient
from zanackb.zanac_game import ZanacGame

ROM = "source/zanac.rom"

client, proc = OpenMsxClient.connect_subprocess(rom=ROM, timeout=20.0)
game = ZanacGame(client, proc)
msx = client
try:
    msx.cmd("set ::cold 0")
    bp = msx.set_breakpoint(0x4010, "set ::cold 1")
    msx.power_on()
    msx.poll_flag("cold", interval=0.3, timeout=12.0)
    msx.remove_breakpoint(bp)
    game.wait_for_title()
    game.start_game()
    time.sleep(0.8)
    msx.write_byte(0xE305, msx.read_byte(0xE305) | 0x80)  # invincible

    print("=== Before credits ===")
    for ch in range(5):
        addr = 0xE20C + ch * 0x1B
        d = bytes(msx.read_memory(addr, 4))
        print(f"  ch{ch} E{addr-0xE000:03X}: {d.hex()}")

    # Verify trampoline fires by breaking right after it would run
    msx.cmd("set ::trampoline_done 0")
    # Place a sentinel byte at 0xC00B (after our trampoline) — if PC hits it, trampoline ran
    # Actually: break at play_sound_event return address 0xC008
    bp_check = msx.set_breakpoint(0xC008, "set ::trampoline_done 1; debug break")

    with open("scripts/credits.tcl") as f:
        msx.cmd(f.read())
    msx.cmd("credits")

    hit = msx.poll_flag("trampoline_done", interval=0.1, timeout=3.0)
    msx.remove_breakpoint(bp_check)
    print(f"\n=== Trampoline {'FIRED' if hit else 'DID NOT FIRE'} ===")

    if hit:
        # CPU is paused at 0xC008 (right after CALL sub_5189 returns, before JP 0x4074)
        pc = int(msx.cmd("reg pc"))
        print(f"  PC=0x{pc:04X} (expected 0xC008)")
        print("  Sound channels at this moment:")
        for ch in range(5):
            addr = 0xE20C + ch * 0x1B
            d = bytes(msx.read_memory(addr, 8))
            print(f"    ch{ch} E{addr-0xE000:03X}: {d.hex()}")
        msx.cont()
    else:
        msx.cont()

    time.sleep(1.0)

    print("\n=== After credits active (1 s later) ===")
    e712 = msx.read_byte(0xE712)
    e701 = msx.read_byte(0xE701)
    e102 = msx.read_byte(0xE102)
    print(f"  E712=0x{e712:02X}  E701=0x{e701:02X}  E102=0x{e102:02X}")
    for ch in range(5):
        addr = 0xE20C + ch * 0x1B
        d = bytes(msx.read_memory(addr, 4))
        active = d[0] != 0
        print(f"  ch{ch}: {d.hex()} {'← ACTIVE' if active else ''}")

    print()
    if e712 == 0x80: print("PASS: fast scroll (E712=0x80)")
    if e102 & 0x08:  print("PASS: credits flag set (E102 bit3)")
    if any(msx.read_byte(0xE20C + i * 0x1B) != 0 for i in range(5)):
        print("PASS: sound channel active")
    else:
        print("FAIL: all sound channels idle")

finally:
    game.cleanup(); proc.terminate(); proc.wait()
