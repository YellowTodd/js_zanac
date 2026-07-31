"""Sprint 0022 — Base encounter projectile system.

Phase 1: Static — read ROM at 0xBFA0-0xBFFF, decode with openMSX disassembler.
Phase 2: Live  — inject base-encounter state; arm read watchpoints on 0xE71E
         and 0xE780 to catch the attack-list consumer.

Key facts from KB:
  place_tile_group (0x95ED) sets:
    (0xE71E:0xE71F) = 0xE780   (LE pointer to attack list in RAM)
    (0xE780+)       = 3-byte entries (Y, X, tile)
    0xE151          = entry count
    0xE150          = 1 (base active)
  handler_type11_base_spawner (0x7AD4) reads 0xE130 for Y/X → not the list consumer.
  The mystery consumer is "near 0xBFA0", uses IX+0x25 (= 0xE125 when IX=0xE100).
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from zanackb.zanac_game import ZanacGame

ENTITY_BASE = 0xE300
SLOT_SIZE   = 32
NUM_SLOTS   = 26


def disasm_range(msx, start: int, length: int) -> str:
    """Disassemble a range via openMSX TCL disassemble command."""
    try:
        result = msx.cmd(f"disassemble {start} {length}")
        return result
    except Exception as e:
        return f"(disassemble failed: {e})"


def decode_rom_bytes(data: bytes, base: int) -> list[str]:
    """Minimal Z80 single-byte / prefix decode for logging."""
    lines = []
    i = 0
    while i < len(data):
        addr = base + i
        b = data[i]
        raw = f"{b:02X}"
        lines.append(f"  {addr:04X}: {raw}")
        i += 1
    return lines


def read_attack_list(msx, ptr_addr: int = 0xE71E) -> tuple[int, bytes]:
    """Read the 16-bit LE attack-list pointer and the first 32 bytes there."""
    lo = msx.read_byte(ptr_addr)
    hi = msx.read_byte(ptr_addr + 1)
    list_addr = (hi << 8) | lo
    data = msx.read_memory(list_addr, 32) if list_addr >= 0xE000 else b""
    return list_addr, data


def slot_summary(raw: bytes) -> list[str]:
    lines = []
    for i in range(NUM_SLOTS):
        slot = raw[i * SLOT_SIZE:(i + 1) * SLOT_SIZE]
        typ  = slot[0] & 0x7F
        if typ == 0:
            continue
        y, x = slot[1], slot[2]
        sat  = slot[3]
        lines.append(
            f"  slot {i:2d}: type {typ:3d} (0x{typ:02X})  active={(slot[0]>>7)}  "
            f"Y={y:3d} X={x:3d}  sat={sat:02X}  +0C={slot[0x0C]:02X}"
        )
    return lines


def main():
    print("Launching openMSX...")
    with ZanacGame.launch() as game:
        msx = game.client

        # ── Phase 1: static ROM decode ────────────────────────────────────────
        print("\n=== Phase 1: Static ROM read 0xBFA0-0xBFFF ===\n")

        # Try openMSX disassembler on the mystery range
        print("openMSX disassemble 0xBFA0 (32 bytes):")
        try:
            dis_out = msx.cmd("disassemble 0xBFA0 32")
            print(dis_out)
        except Exception as e:
            print(f"  disassemble command unavailable: {e}")

        # Hex dump as fallback
        bfa0_data = msx.read_memory(0xBFA0, 0x60)
        print(f"\nROM hex 0xBFA0-0xBFFF:")
        for i in range(0, len(bfa0_data), 16):
            chunk = bfa0_data[i:i+16]
            addr  = 0xBFA0 + i
            print(f"  {addr:04X}: {' '.join(f'{b:02X}' for b in chunk)}")

        # Check the subroutine structure near 0xBFAB
        print("\nChecking callers of base_encounter_ctrl:")
        for addr in [0xBFAB, 0xBFB3, 0xBFBF, 0xBFC2, 0xBFC8]:
            data = msx.read_memory(addr, 8)
            print(f"  {addr:04X}: {' '.join(f'{b:02X}' for b in data)}")

        # ── Phase 2: gameplay with watchpoints ────────────────────────────────
        print("\n=== Phase 2: Gameplay — watchpoints on 0xE71E and 0xE780 ===\n")

        print("Waiting for title...")
        game.wait_for_title()
        time.sleep(0.5)
        print("Starting game...")
        game.start_game()
        time.sleep(2.5)

        # Read initial state
        e71e_lo = msx.read_byte(0xE71E)
        e71e_hi = msx.read_byte(0xE71F)
        print(f"Initial (0xE71E:F) = 0x{e71e_hi:02X}{e71e_lo:02X}")

        e150 = msx.read_byte(0xE150)
        e151 = msx.read_byte(0xE151)
        print(f"Initial 0xE150={e150:#04x}  0xE151={e151:#04x}")

        # Arm write watchpoints on E71E to catch place_tile_group
        msx.cmd("set ::e71e_writer_pc 0")
        msx.cmd("set ::e71e_writer_fired 0")
        wp_write = msx.cmd(
            "debug set_watchpoint write_mem 0xe71e {} "
            "{set ::e71e_writer_pc [reg PC]; set ::e71e_writer_fired 1; debug break}"
        )
        print(f"Armed write-watchpoint on 0xE71E: {wp_write}")

        # Also watch 0xE780 writes (where attack list entries go)
        msx.cmd("set ::e780_writer_pc 0")
        msx.cmd("set ::e780_writer_fired 0")
        wp_e780 = msx.cmd(
            "debug set_watchpoint write_mem 0xe780 {} "
            "{set ::e780_writer_pc [reg PC]; set ::e780_writer_fired 1; debug break}"
        )
        print(f"Armed write-watchpoint on 0xE780: {wp_e780}")

        # Watch READ of 0xE71E
        msx.cmd("set ::e71e_reader_pc 0")
        msx.cmd("set ::e71e_reader_fired 0")
        wp_read71e = msx.cmd(
            "debug set_watchpoint read_mem 0xe71e {} "
            "{set ::e71e_reader_pc [reg PC]; set ::e71e_reader_fired 1; debug break}"
        )
        print(f"Armed read-watchpoint on 0xE71E: {wp_read71e}")

        # ── Inject base-encounter state ───────────────────────────────────────
        print("\nInjecting base-encounter state...")
        # (0xE71E:F) = LE pointer to 0xE780
        msx.write_memory(0xE71E, bytes([0x80, 0xE7]))
        # Attack-list entries at 0xE780: 4 × 3 bytes (Y, X, tile)
        msx.write_memory(0xE780, bytes([
            0x60, 0x60, 0x44,   # entry 0: Y=96, X=96,  tile=0x44
            0x60, 0x78, 0x44,   # entry 1: Y=96, X=120
            0x60, 0x90, 0x44,   # entry 2
            0x60, 0xA8, 0x44,   # entry 3
        ]))
        msx.write_byte(0xE151, 0x04)   # 4 attack entries
        msx.write_byte(0xE152, 0x04)   # snapshot count
        msx.write_byte(0xE150, 0x01)   # base active (bit 0)
        print("  0xE71E → 0xE780  |  0xE780 = 4 fake entries  |  0xE150=1")

        # Resume and wait for a watchpoint to fire
        msx.cont()
        deadline = time.time() + 6.0
        fired = False
        while time.time() < deadline and not fired:
            time.sleep(0.15)
            for flag, name in [
                ("e71e_writer_fired", "WRITE 0xE71E"),
                ("e780_writer_fired", "WRITE 0xE780"),
                ("e71e_reader_fired", "READ  0xE71E"),
            ]:
                val = msx.cmd(f"set ::{flag}")
                if val == "1":
                    pc_var = flag.replace("_fired", "_pc")
                    pc = int(msx.cmd(f"set ::{pc_var}"))
                    print(f"\n*** Watchpoint fired: {name}  PC=0x{pc:04X} ***")

                    # Dump context: registers and surrounding bytes
                    for reg in ["PC", "SP", "AF", "BC", "DE", "HL", "IX", "IY"]:
                        try:
                            rv = msx.cmd(f"reg {reg}")
                            print(f"    {reg}={rv}")
                        except Exception:
                            pass

                    # Show a few bytes before/after the PC
                    ctx = msx.read_memory(max(0x4000, pc - 4), 16)
                    print(f"    ROM context:")
                    print(f"      {' '.join(f'{b:02X}' for b in ctx)}  (from 0x{max(0x4000,pc-4):04X})")

                    msx.cmd(f"set ::{flag} 0")
                    fired = True
                    break

        if not fired:
            print("\nNo watchpoint fired within 6s. Current state:")
            e150 = msx.read_byte(0xE150)
            e151 = msx.read_byte(0xE151)
            e71e_lo = msx.read_byte(0xE71E)
            e71e_hi = msx.read_byte(0xE71F)
            print(f"  0xE150={e150:#04x}  0xE151={e151:#04x}  (0xE71E:F)=0x{e71e_hi:02X}{e71e_lo:02X}")

        # Remove watchpoints
        for wp in [wp_write, wp_e780, wp_read71e]:
            try:
                msx.remove_watchpoint(wp)
            except Exception:
                pass

        # ── Phase 3: entity table snapshot after injection ─────────────────────
        print("\n=== Phase 3: Entity table after injection ===\n")
        # Set BP at entity_dispatch to get a clean snapshot
        msx.cmd("set ::snap_flag 0")
        bp_snap = msx.set_breakpoint(0x445F, "incr ::snap_flag; if {$::snap_flag >= 5} {debug break}")
        msx.cont()
        time.sleep(1.5)
        raw = msx.read_memory(ENTITY_BASE, NUM_SLOTS * SLOT_SIZE)
        msx.remove_breakpoint(bp_snap)

        lines = slot_summary(raw)
        if lines:
            print("Active entity slots:")
            for l in lines:
                print(l)
        else:
            print("  (no active entity slots)")

        # Check for type-11 entities specifically
        for i in range(NUM_SLOTS):
            slot = raw[i * SLOT_SIZE:(i + 1) * SLOT_SIZE]
            typ = slot[0] & 0x7F
            if typ == 11:
                print(f"\nType-11 found at slot {i}! Full slot:")
                for row in range(0, 32, 8):
                    chunk = slot[row:row+8]
                    print(f"  +{row:02X}: {' '.join(f'{b:02X}' for b in chunk)}")

        # Final state
        print(f"\nFinal 0xE150={msx.read_byte(0xE150):#04x}  0xE151={msx.read_byte(0xE151):#04x}")
        list_addr, list_data = read_attack_list(msx)
        print(f"Attack list pointer: 0x{list_addr:04X}")
        if list_data:
            print(f"Attack list (first 24 bytes): {' '.join(f'{b:02X}' for b in list_data[:24])}")


if __name__ == "__main__":
    main()
