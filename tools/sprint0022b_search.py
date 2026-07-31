"""Sprint 0022 pass 2 — ROM search for 0xE71E/0xE780 consumers
and decode of 0xBFA0-0xBFF4 via openMSX.
Also: natural base-encounter watchpoint (wait up to 30s for scroll engine).
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from zanackb.zanac_game import ZanacGame

ENTITY_BASE = 0xE300
SLOT_SIZE   = 32
NUM_SLOTS   = 26


def search_rom_for_bytes(msx, needle: bytes, label: str, start=0x4000, end=0xC000, chunk=256):
    """Scan ROM for a byte pattern; print matches."""
    print(f"  Searching for {label} ({needle.hex(' ')}):")
    hits = []
    addr = start
    while addr < end:
        size = min(chunk, end - addr)
        data = bytes(msx.read_memory(addr, size))
        pos  = 0
        while True:
            idx = data.find(needle, pos)
            if idx < 0:
                break
            hits.append(addr + idx)
            pos = idx + 1
        addr += size
    if hits:
        for h in hits:
            ctx = bytes(msx.read_memory(h - 2, 12))
            print(f"    0x{h:04X}: ctx={ctx.hex(' ')}")
    else:
        print("    (not found)")
    return hits


def decode_bfa0(data: bytes, base: int = 0xBFA0):
    """Manual Z80 decode of the 0xBFA0-0xBFF4 block."""
    print(f"\nManual decode 0x{base:04X}-0x{base+len(data)-1:04X}:")

    # Known structure from hex analysis
    annotations = {
        0xBFA0: "SUB_bfa0: CALL 0x4496 (alloc_entity_slot)",
        0xBFA3: "RET C  (no free slot → return)",
        0xBFA4: "RES 0, (IX+0x25)  [clears spawn_trigger 0xE125 bit0; IX=0xE100]",
        0xBFA8: "LD (HL), 0x44  [write entity type 0x44=68dec to new slot]",
        0xBFAA: "RET",
        0xBFAB: "SUB_bfab: LD HL, 0xE12E",
        0xBFAE: "CALL 0xBFCB  (base_encounter_ctrl: increment 0xE12E)",
        0xBFB1: "JR +6 → 0xBFB9",
        0xBFB3: "SUB_bfb3: LD HL, 0xE12E",
        0xBFB6: "CALL 0xBFC2  (base_encounter_ctrl: decrement 0xE12E)",
        0xBFB9: "LD HL, 0xE12D  (spawn_ctrl)",
        0xBFBC: "SET 0, (HL)  [set spawn_ctrl bit0]",
        0xBFBE: "RET",
        0xBFBF: "SUB_bfbf: LD HL, 0xE130  (base_health_ctr)",
        0xBFC2: "SUB_bfc2: LD A, (HL)  [generic counter decrement entry]",
        0xBFC3: "AND A  [test if zero]",
        0xBFC4: "JR Z, 0xBFD6  [if 0, skip to display]",
        0xBFC6: "JR 0xBFD5  [else decrement]",
        0xBFC8: "SUB_bfc8: LD HL, 0xE130  (base_encounter_ctrl fixed-arg entry)",
        0xBFCB: "SUB_bfcb: LD A, (0xE150)  (base_encounter_ctrl gated entry)",
        0xBFCC: "BIT 1, A  [test base_encounter_flags bit1]",
        0xBFCE: "JR NZ, 0xBFD6  [if bit1 set → skip increment]",
        0xBFD0: "INC (HL)  [increment counter]",
        0xBFD2: "JR NZ, 0xBFD6  [if nonzero after inc → display]",
        0xBFD4: "(note: JR offset decodes oddly here — check raw bytes)",
        0xBFD5: "DEC (HL)  [overflow guard: saturate at 0xFF]",
        0xBFD6: "LD HL, 0x3839  [VDP name-table row 1, col 25 area]",
        0xBFD9: "CALL 0x5C25  [VDP address prep]",
        0xBFDF: "LD HL, 0x3859  [VDP name-table row 2]",
        0xBFE2: "CALL 0x0053  [BIOS WRTVRM → write HUD counter]",
        0xBFE5: "LD A, (0xE12E); CALL 0x4C74  [write spawn_pos_hi digit]",
        0xBFEB: "LD A, (0xE132); CALL 0x4C74  [write scroll_offset digit]",
        0xBFF1: "LD A, (0xE130); CALL 0x4C74  [write base_health_ctr digit]",
        0xBFF4: "JP 0x42F8  [vdp_int_enable → return]",
    }
    for addr, note in sorted(annotations.items()):
        off = addr - base
        if 0 <= off < len(data):
            raw = data[off:off+4]
            print(f"  {addr:04X}: {raw.hex(' '):<12s}  {note}")


def main():
    print("Launching openMSX...")
    with ZanacGame.launch() as game:
        msx = game.client

        # ── ROM search ────────────────────────────────────────────────────────
        print("\n=== ROM byte-pattern search ===\n")

        # LD HL, (0xE71E) = 2A 1E E7
        search_rom_for_bytes(msx, bytes([0x2A, 0x1E, 0xE7]),
                             "LD HL,(0xE71E)")
        # LD A, (0xE71E) = 3A 1E E7
        search_rom_for_bytes(msx, bytes([0x3A, 0x1E, 0xE7]),
                             "LD A,(0xE71E)")
        # LD DE,(0xE71E) = ED 5B 1E E7
        search_rom_for_bytes(msx, bytes([0xED, 0x5B, 0x1E, 0xE7]),
                             "LD DE,(0xE71E)")
        # LD (0xE71E),HL = 22 1E E7
        search_rom_for_bytes(msx, bytes([0x22, 0x1E, 0xE7]),
                             "LD (0xE71E),HL")
        # LD (0xE71E),A = 32 1E E7
        search_rom_for_bytes(msx, bytes([0x32, 0x1E, 0xE7]),
                             "LD (0xE71E),A")
        # CALL 0xBFA0 = CD A0 BF
        search_rom_for_bytes(msx, bytes([0xCD, 0xA0, 0xBF]),
                             "CALL 0xBFA0 (sub_bfa0)")
        # CALL 0xBFAB = CD AB BF
        search_rom_for_bytes(msx, bytes([0xCD, 0xAB, 0xBF]),
                             "CALL 0xBFAB (sub_bfab)")
        # CALL 0xBFB3 = CD B3 BF
        search_rom_for_bytes(msx, bytes([0xCD, 0xB3, 0xBF]),
                             "CALL 0xBFB3 (sub_bfb3)")
        # CALL 0xBFBF = CD BF BF
        search_rom_for_bytes(msx, bytes([0xCD, 0xBF, 0xBF]),
                             "CALL 0xBFBF (sub_bfbf)")

        # ── Annotated decode ──────────────────────────────────────────────────
        bfa0_data = bytes(msx.read_memory(0xBFA0, 0x55))
        decode_bfa0(bfa0_data, 0xBFA0)

        # ── Natural base encounter — short wait ───────────────────────────────
        print("\n=== Natural base: wait 20s for scroll to reach base ===\n")
        print("Waiting for title...")
        game.wait_for_title()
        game.start_game()

        # Arm a read watchpoint on 0xE71E (only game code this time, no inject)
        msx.cmd("set ::e71e_read_pc 0")
        msx.cmd("set ::e71e_read_fired 0")
        wp = msx.cmd(
            "debug set_watchpoint read_mem 0xe71e {} "
            "{set ::e71e_read_pc [reg PC]; set ::e71e_read_fired 1; debug break}"
        )
        # Also arm a watchpoint when 0xE150 is set to non-zero (base activation)
        msx.cmd("set ::e150_set_pc 0")
        msx.cmd("set ::e150_set_fired 0")
        wp2 = msx.cmd(
            "debug set_watchpoint write_mem 0xe150 "
            "{[debug read memory 0xe150] != 0} "
            "{set ::e150_set_pc [reg PC]; set ::e150_set_fired 1; debug break}"
        )

        msx.cont()
        print("Watching for base encounter (up to 30s)...")
        deadline = time.time() + 30.0
        fired = False
        while time.time() < deadline and not fired:
            time.sleep(0.5)
            for flag, name, pc_var in [
                ("e71e_read_fired", "READ 0xE71E", "e71e_read_pc"),
                ("e150_set_fired",  "WRITE 0xE150≠0", "e150_set_pc"),
            ]:
                val = msx.cmd(f"set ::{flag}")
                if val == "1":
                    pc = int(msx.cmd(f"set ::{pc_var}"))
                    print(f"\n*** {name}  PC=0x{pc:04X} ***")
                    for reg in ["PC","SP","AF","BC","DE","HL","IX","IY"]:
                        try:
                            print(f"    {reg}={int(msx.cmd(f'reg {reg}')):04X}")
                        except Exception:
                            pass
                    ctx = bytes(msx.read_memory(max(0x4000, pc - 2), 12))
                    print(f"    context from 0x{max(0x4000,pc-2):04X}: {ctx.hex(' ')}")
                    msx.cmd(f"set ::{flag} 0")
                    fired = True
                    break

        if not fired:
            e150 = msx.read_byte(0xE150)
            e71e_lo = msx.read_byte(0xE71E)
            e71e_hi = msx.read_byte(0xE71F)
            print(f"No watchpoint in 30s. 0xE150={e150:#04x}  (0xE71E:F)=0x{e71e_hi:02X}{e71e_lo:02X}")

        try:
            msx.remove_watchpoint(wp)
            msx.remove_watchpoint(wp2)
        except Exception:
            pass


if __name__ == "__main__":
    main()
