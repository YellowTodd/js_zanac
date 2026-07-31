#!/usr/bin/env python3
"""Sprint 0010 — live-debug investigation scripts.

Each function targets one of the 5 priority open questions.
Run individual questions by calling the function after connecting.
"""

import sys
import os
import time

sys.path.insert(0, str(__file__).rsplit("/tools/", 1)[0] + "/tools")
from zanackb.openmsx import OpenMsxClient, OpenMsxError


def connect() -> OpenMsxClient:
    return OpenMsxClient.autoconnect()


# ─── Q1: Who sets bit 0 of (0xE700)? ──────────────────────────────────────────

def q1_find_e700_writer(client: OpenMsxClient) -> None:
    """Install write-watchpoint on 0xE700; fires only when bit 0 is SET."""
    print("=== Q1: Who sets bit 0 of (0xE700)? ===")
    # Condition: new value has bit 0 set (ignoring the ISR clear)
    # We want the writer that SETS bit 0 (the DMA-ready signal).
    wp = client.cmd(
        "debug set_watchpoint write_mem 0xe700 "
        "{[expr {([debug read memory 0xe700] & 0x01) != 0}]} "
        "{set ::e700_writer [reg PC]; debug break}"
    )
    print(f"Watchpoint installed: {wp}")
    print("Let the game run (scrolling active). I'll detect the break...")
    client.cont()

    # Poll for break: PC will not be at a scroll-wait address when we stop
    time.sleep(0.5)
    try:
        pc = client.cmd("reg PC")
        writer = client.cmd("set ::e700_writer")
        print(f"BREAK — current PC: {pc}")
        print(f"Writer PC (when bit0 was SET): 0x{int(writer):04X}")
        # Disassemble a few bytes around the writer
        disasm = client.cmd(f"disasm 0x{int(writer):04X} 5")
        print(f"Disasm @ writer:\n{disasm}")
    except OpenMsxError as e:
        print(f"Not broken yet or error: {e}")

    client.cmd(f"debug remove_watchpoint {wp}")
    print(f"Watchpoint {wp} removed.")


# ─── Q2: Is 0xE620 a direct name-table shadow? ─────────────────────────────────

def q2_name_table_shadow(client: OpenMsxClient) -> None:
    """Dump 0xE620 (RAM) and VRAM 0x3800 and compare."""
    print("=== Q2: Is 0xE620 a direct name-table shadow? ===")
    # Pause the machine first
    client.cmd("debug break")
    time.sleep(0.1)

    ram = client.read_memory(0xE620, 768)
    vram = client.read_debuggable("VRAM", 0x3800, 768)

    matches = sum(1 for a, b in zip(ram, vram) if a == b)
    total = 768
    print(f"RAM 0xE620 vs VRAM 0x3800: {matches}/{total} bytes match ({100*matches//total}%)")

    if matches == total:
        print("RESULT: Perfect match — 0xE620 IS a direct 32×24 name-table shadow.")
    elif matches > 700:
        print("RESULT: Near-match — shadow with minor differences (possibly write-lag).")
    else:
        print("RESULT: Poor match — 0xE620 is NOT a simple shadow of 0x3800.")

    # Show first 64 bytes of each for manual inspection
    print(f"\nRAM[0xE620..0xE63F]  = {ram[:64].hex()}")
    print(f"VRAM[0x3800..0x383F] = {vram[:64].hex()}")

    # Also check if it's offset (maybe the shadow is at a different VRAM addr)
    for vram_base, label in [(0x1800, "SCR2 name"), (0x0000, "SCR2 pg0"), (0x3800, "SCR1 name")]:
        try:
            v2 = client.read_debuggable("VRAM", vram_base, 768)
            m2 = sum(1 for a, b in zip(ram, v2) if a == b)
            print(f"  vs VRAM 0x{vram_base:04X} ({label}): {m2}/{total} match")
        except OpenMsxError:
            pass

    client.cont()


# ─── Q3: Entity slot live dump (offsets 3–27) ──────────────────────────────────

def q3_entity_slot_dump(client: OpenMsxClient) -> None:
    """Breakpoint at entity_dispatch (0x445F); dump all 26 slots."""
    print("=== Q3: Entity slot live dump (offsets 3–27) ===")
    bp = client.set_breakpoint(0x445F, "debug break")
    print(f"Breakpoint at entity_dispatch: {bp}")
    client.cont()

    # Wait for break
    time.sleep(1.5)
    pc = client.cmd("reg PC")
    print(f"Break at PC=0x{int(pc):04X}")

    # Dump all 26 entity slots (26 × 32 bytes = 832 bytes)
    raw = client.read_memory(0xE300, 832)

    print("\nSlot | Type | off0-2 | off3-5 | off6-11 | off12 | off13-27")
    print("-----|------|--------|--------|---------|-------|----------")
    active_slots = []
    for i in range(26):
        slot = raw[i*32:(i+1)*32]
        typ = slot[0]
        if typ == 0:
            continue
        off_0_2  = slot[0:3].hex()
        off_3_5  = slot[3:6].hex()
        off_6_11 = slot[6:12].hex()
        off_12   = slot[12]
        off_13_27 = slot[13:28].hex()
        print(f"  {i:2d} | 0x{typ:02X} | {off_0_2} | {off_3_5} | {off_6_11} | 0x{off_12:02X}  | {off_13_27}")
        active_slots.append((i, typ, slot))

    print(f"\nActive slots: {len(active_slots)}")

    # Also show the player slot (slot 0, type 1) in detail
    if raw[0] == 1:
        slot = raw[0:32]
        print("\nPlayer slot (type=1, 0xE300) byte-by-byte:")
        for off in range(32):
            print(f"  IX+0x{off:02X} = 0x{slot[off]:02X}  ({slot[off]:3d})")

    client.remove_breakpoint(bp)
    client.cont()


# ─── Q4: Scroll state 0xE704–0xE713 diff ──────────────────────────────────────

def q4_scroll_state_diff(client: OpenMsxClient) -> None:
    """Snapshot 0xE700-0xE71A at 3 moments in a scroll cycle."""
    print("=== Q4: Scroll state 0xE704–0xE713 diff ===")

    def snap(label: str) -> bytes:
        client.cmd("debug break")
        time.sleep(0.1)
        data = client.read_memory(0xE700, 0x1B)
        print(f"\n{label}: {data.hex()}")
        client.cont()
        return data

    # Snapshot A: before scroll_sync (set BP just before it)
    bp_sync = client.set_breakpoint(0x9A00, "debug break")  # scroll_sync entry
    client.cont()
    time.sleep(0.5)
    a = client.read_memory(0xE700, 0x1B)
    print(f"\nSnap A (at scroll_sync entry 0x9A00): {a.hex()}")
    client.remove_breakpoint(bp_sync)

    # Snapshot B: after scroll_sync returns
    client.cont()
    time.sleep(0.05)
    client.cmd("debug break")
    time.sleep(0.05)
    b = client.read_memory(0xE700, 0x1B)
    print(f"Snap B (just after scroll_sync): {b.hex()}")

    # Snapshot C: after one frame
    client.cont()
    time.sleep(0.1)
    client.cmd("debug break")
    time.sleep(0.05)
    c = client.read_memory(0xE700, 0x1B)
    print(f"Snap C (one frame later): {c.hex()}")
    client.cont()

    print("\nDiff table (changed bytes):")
    print("Offset | Address | A    | B    | C    | Delta")
    any_change = False
    for i in range(0x1B):
        if a[i] != b[i] or b[i] != c[i] or a[i] != c[i]:
            print(f"  0x{i:02X}  | 0xE{700+i:03X}  | 0x{a[i]:02X} | 0x{b[i]:02X} | 0x{c[i]:02X} | {'changed' if a[i]!=c[i] else 'transient'}")
            any_change = True
    if not any_change:
        print("  (no changes detected between snapshots)")


# ─── Q5: Base encounter consumer (0xE150 watcher) ──────────────────────────────

def q5_base_encounter_consumer(client: OpenMsxClient) -> None:
    """Read-watchpoint on 0xE150; fires when something reads the base flag."""
    print("=== Q5: Base encounter consumer (0xE150 read-watcher) ===")
    wp = client.cmd(
        "debug set_watchpoint read_mem 0xe150 {} "
        "{set ::e150_reader [reg PC]; debug break}"
    )
    print(f"Watchpoint installed: {wp}")
    print("Play until a base appears on screen. I'll break when 0xE150 is read...")
    client.cont()

    # This one needs the user to play to a base
    # We just set up the watchpoint and the user will notify us
    print("(waiting — tell me when the break fires)")


def q5_read_result(client: OpenMsxClient) -> None:
    """Call after Q5 fires; reads the captured PC and disassembles."""
    pc = client.cmd("reg PC")
    reader = client.cmd("set ::e150_reader")
    print(f"Break at PC: {pc}")
    print(f"Reader PC (0xE150 was read at): 0x{int(reader):04X}")
    disasm = client.cmd(f"disasm 0x{int(reader)-4:04X} 10")
    print(f"Disasm around reader:\n{disasm}")
    client.cont()


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Sprint 0010 live-debug helper")
    p.add_argument("question", choices=["q1","q2","q3","q4","q5","q5r","all"],
                   help="Which question to run (q5r = read Q5 result after break)")
    args = p.parse_args()

    client = connect()
    print(f"Connected to openMSX.")

    if args.question == "q1":
        q1_find_e700_writer(client)
    elif args.question == "q2":
        q2_name_table_shadow(client)
    elif args.question == "q3":
        q3_entity_slot_dump(client)
    elif args.question == "q4":
        q4_scroll_state_diff(client)
    elif args.question == "q5":
        q5_base_encounter_consumer(client)
    elif args.question == "q5r":
        q5_read_result(client)
    elif args.question == "all":
        q2_name_table_shadow(client)
        q3_entity_slot_dump(client)

    client.close()
