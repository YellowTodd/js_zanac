"""
Sprint 0033 — Capture exact credits-setup state using the game-end save state.

Loads savestates/game-end.oms (player just beat the final boss, invincibility
patch applied).  The scroll engine should trigger LAB_92AF within seconds.

Breakpoints:
  0x9216  CALL sub_9433  — after sub_516c and BIOS copy ran
  0x9219  CALL sub_946e  — after sub_9433 set level stream to 0xBBB4
  0x924B  CALL sub_5189  — after sub_946e filled E800 and LDIR/BIOS copies ran
  0x92AF  LAB_92af       — full setup done; capture all state + VRAM + E800
"""

import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from zanackb.openmsx import OpenMsxClient
from zanackb.zanac_game import ZanacGame

ROM       = "source/zanac.rom"
IPS       = "scripts/invincible.ips"
SAVESTATE = "savestates/game-end.oms"

ADDR_CALL_9433 = 0x9216
ADDR_CALL_946E = 0x9219
ADDR_CALL_5189 = 0x924B   # play_sound_event(0x0C)
ADDR_LAB_92AF  = 0x92AF


def dump(msx, label):
    print(f"\n{'─'*64}")
    print(f"  {label}")
    print(f"{'─'*64}")
    ix  = int(msx.cmd("reg ix"))
    sp  = int(msx.cmd("reg sp"))
    pc  = int(msx.cmd("reg pc"))
    print(f"  IX=0x{ix:04X}  SP=0x{sp:04X}  PC=0x{pc:04X}")
    for addr, name in [
        (0xE700,'scroll_flags'), (0xE701,'stage'),     (0xE702,'row_ctr'),
        (0xE710,'scroll_spd'),   (0xE712,'target_spd'), (0xE722,'e722'),
        (0xE102,'e102'),
    ]:
        v = msx.read_byte(addr)
        print(f"  {name:14s} 0x{addr:04X} = 0x{v:02X}")
    # stream_ptr (16-bit)
    sp_v = msx.read_byte(0xE704) | (msx.read_byte(0xE705) << 8)
    print(f"  {'stream_ptr':14s} 0xE704 = 0x{sp_v:04X}")
    # IX offsets
    if 0xE700 <= ix < 0xE800:
        for off in [0x50, 0x56, 0x57]:
            v = msx.read_byte(ix + off)
            print(f"  (IX+0x{off:02X})       0x{ix+off:04X} = 0x{v:02X}")
    # Sound slot 0
    s0 = bytes(msx.read_memory(0xE20C, 4))
    print(f"  E20C[0:4] (snd0)  {s0.hex()}")
    # E800 first 32 bytes
    e800 = bytes(msx.read_memory(0xE800, 32))
    print(f"  E800[0:32]        {e800.hex()}")
    # VRAM 0x3C00 first 32 bytes
    vram = bytes(msx.read_memory(0x3C00, 32))
    print(f"  VRAM[3C00:3C20]   {vram.hex()}")


def main():
    client, proc = OpenMsxClient.connect_subprocess(
        rom=ROM,
        extra_args=("-ips", IPS, "-savestate", SAVESTATE),
        timeout=30.0,
    )
    game = ZanacGame(client, proc)
    msx  = client
    try:
        # Save state loads automatically; power on to activate it
        msx.cmd("set ::cold 0")
        bp = msx.set_breakpoint(0x4010, "set ::cold 1")
        msx.power_on()
        msx.poll_flag("cold", interval=0.3, timeout=15.0)
        msx.remove_breakpoint(bp)
        print("Loaded. Waiting for LAB_91fd (scroll engine end-game trigger)...")

        # ── Stage 1: before sub_9433 ──────────────────────────────────────
        msx.cmd("set ::at_9433 0")
        bp1 = msx.set_breakpoint(ADDR_CALL_9433,
                                  "set ::at_9433 1; debug break")
        msx.cont()
        msx.poll_flag("at_9433", interval=1.0, timeout=120.0)
        msx.remove_breakpoint(bp1)
        dump(msx, "BEFORE sub_9433  [sub_516c + CALL 0x005C done]")

        # ── Stage 2: before sub_946e ──────────────────────────────────────
        msx.cmd("set ::at_946e 0")
        bp2 = msx.set_breakpoint(ADDR_CALL_946E,
                                  "set ::at_946e 1; debug break")
        msx.cont()
        msx.poll_flag("at_946e", interval=0.5, timeout=15.0)
        msx.remove_breakpoint(bp2)
        dump(msx, "BEFORE sub_946e  [sub_9433 done: E701=8, E704=0xBBB6]")

        # ── Stage 3: before play_sound_event(0x0C) ────────────────────────
        msx.cmd("set ::at_5189 0")
        bp3 = msx.set_breakpoint(ADDR_CALL_5189,
                                  "set ::at_5189 1; debug break")
        msx.cont()
        msx.poll_flag("at_5189", interval=1.0, timeout=30.0)
        msx.remove_breakpoint(bp3)
        dump(msx, "BEFORE play_sound_event  [sub_946e done, LDIR+BIOS copy done]")
        a_val = int(msx.cmd("reg a"))
        print(f"  A (sound event #) = 0x{a_val:02X}")

        # ── Stage 4: LAB_92AF (full setup done) ───────────────────────────
        msx.cmd("set ::at_92af 0")
        bp4 = msx.set_breakpoint(ADDR_LAB_92AF,
                                  "set ::at_92af 1; debug break")
        msx.cont()
        msx.poll_flag("at_92af", interval=0.5, timeout=10.0)
        msx.remove_breakpoint(bp4)
        dump(msx, "AT LAB_92AF  [all setup complete]")

        # ── Full captures ─────────────────────────────────────────────────
        print("\n=== Full E800 tile buffer (0x240 bytes) ===")
        e800_full = bytes(msx.read_memory(0xE800, 0x240))
        for i in range(0, 0x240, 16):
            print(f"  E{0x800+i:03X}: {e800_full[i:i+16].hex()}")

        print("\n=== VRAM 0x3C00 sprite pattern table (0x240 bytes) ===")
        vram_full = bytes(msx.read_memory(0x3C00, 0x240))
        for i in range(0, 0x240, 16):
            print(f"  3C{(i>>4):02X}0: {vram_full[i:i+16].hex()}")
            if all(b == 0 for b in vram_full[i:i+16]):
                pass  # still print zeros (important to know)

        print("\n=== Sound channel slots 0xE20C (5 × 0x1B bytes) ===")
        for ch in range(5):
            addr = 0xE20C + ch * 0x1B
            data = bytes(msx.read_memory(addr, 0x1B))
            print(f"  ch{ch} E{addr-0xE000:03X}: {data.hex()}")

        print("\n=== Key RAM variables ===")
        for addr, name in [
            (0xE700,'scroll_flags'), (0xE701,'stage'), (0xE710,'scroll_spd'),
            (0xE712,'target_spd'),   (0xE722,'e722'), (0xE102,'e102'),
        ]:
            print(f"  {name} = 0x{msx.read_byte(addr):02X}")
        ix = int(msx.cmd("reg ix"))
        for off, name in [(0x50,'ix+50'), (0x56,'ix+56'), (0x57,'ix+57')]:
            print(f"  {name} = 0x{msx.read_byte(ix+off):02X}")

    finally:
        game.cleanup(); proc.terminate(); proc.wait()


if __name__ == "__main__":
    main()
