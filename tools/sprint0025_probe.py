#!/usr/bin/env python3
"""
Sprint 0025 — manual entity type probe.

For each target type: inject it into a spare slot, let the game run
one dispatch cycle, read back the initialised slot, print the result.
"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools" / "zanackb"))
from zanac_game import ZanacGame, MSXKey  # noqa: E402

ROM        = ROOT / "source" / "zanac.rom"
ENT_BASE   = 0xE300
SLOT_SIZE  = 0x20
PROBE_SLOT = 24              # use slot 24 (0xE600) — unlikely to be occupied
PROBE_ADDR = ENT_BASE + PROBE_SLOT * SLOT_SIZE   # 0xE600

# Types to probe: still-unknown or recently-hypothesis entries
TARGETS = [16, 17, 18, 36, 42, 43, 45, 57, 58, 59, 61, 62, 63, 64, 67]


def read_slot(msx, addr: int) -> bytes:
    return bytes(msx.read_memory(addr, SLOT_SIZE))


def fmt_slot(slot: bytes, addr: int) -> str:
    typ      = slot[0x00] & 0x7F
    active   = bool(slot[0x00] & 0x80)
    y, x     = slot[0x01], slot[0x02]
    sat_name = slot[0x03]
    sat_col  = slot[0x04]
    bflags   = slot[0x0C]
    vy       = slot[0x09]
    vy_frac  = slot[0x08]
    vx       = slot[0x0B]
    vx_frac  = slot[0x0A]
    anim_lo  = slot[0x11]
    anim_hi  = slot[0x12]
    anim_max = slot[0x10]
    tgt_y    = slot[0x13]
    tgt_x    = slot[0x14]
    y_acc    = slot[0x15]
    x_acc    = slot[0x16]
    child    = (slot[0x1C] << 8) | slot[0x1B]
    col_w    = slot[0x1D]
    pers19   = slot[0x19]
    pers1e   = slot[0x1E]
    pat      = sat_name >> 2

    lines = [
        f"  type_flags 0x{slot[0x00]:02X}  active={active}  type_re-read={typ}",
        f"  Y={y}  X={x}",
        f"  sat_name 0x{sat_name:02X} → pattern {pat}   sat_col 0x{sat_col:02X}",
        f"  bflags 0x{bflags:02X}  (Y:{bflags&1} X:{(bflags>>1)&1}"
        f" anim:{(bflags>>2)&1} Yhom:{(bflags>>3)&1} Xhom:{(bflags>>4)&1})",
        f"  vy={vy} vy_frac=0x{vy_frac:02X}   vx={vx} vx_frac=0x{vx_frac:02X}",
    ]
    if tgt_y or tgt_x or y_acc or x_acc:
        lines.append(f"  homing: tgt_y={tgt_y} tgt_x={tgt_x} y_acc={y_acc} x_acc={x_acc}")
    if anim_max:
        lines.append(f"  anim: max={anim_max}  table=0x{(anim_hi<<8)|anim_lo:04X}")
    if child:
        lines.append(f"  child_ptr=0x{child:04X}  col_wid={col_w}")
    if pers19:
        lines.append(f"  +0x19={pers19}")
    if pers1e:
        lines.append(f"  +0x1E={pers1e}")
    # Show non-zero persistent bytes +0x18..+0x1F
    pers = " ".join(f"{slot[0x18+i]:02X}" for i in range(8))
    lines.append(f"  persistent +0x18..1F: {pers}")
    return "\n".join(lines)


def probe_type(msx, typ: int) -> bytes:
    """Inject type into probe slot, let one dispatch cycle run, return slot."""
    # Clear the probe slot
    msx.write_memory(PROBE_ADDR, bytes(SLOT_SIZE))
    # Place at a visible screen position
    msx.write_byte(PROBE_ADDR + 0x01, 100)   # Y
    msx.write_byte(PROBE_ADDR + 0x02, 120)   # X
    # Write type WITHOUT active flag → triggers init on next dispatch
    msx.write_byte(PROBE_ADDR + 0x00, typ)

    # Wait for entity_dispatch to process this slot (one full cycle)
    msx.cmd("set ::probe_done 0")
    # Break after entity_dispatch has iterated at least PROBE_SLOT+1 slots
    # entity_dispatch iterates 26 slots; we need it to reach slot 24.
    # Count 25 individual entity calls from 0x445F (slots 0..24).
    count_target = PROBE_SLOT + 2    # +2 for safety
    bp = msx.cmd(
        f"debug set_bp 0x445F true "
        f"{{incr ::probe_n; if {{$::probe_n >= {count_target}}} "
        f"{{set ::probe_done 1; debug break}}}}"
    )
    msx.cmd("set ::probe_n 0")
    msx.cont()
    time.sleep(1.0)
    msx.cmd(f"debug remove_bp {bp}")

    return read_slot(msx, PROBE_ADDR)


def main():
    with ZanacGame.launch(str(ROM)) as game:
        msx = game.client
        game.wait_for_title()
        game.start_game()
        # Keep player alive and let the game settle
        msx.write_byte(0xE305, msx.read_byte(0xE305) | 0x80)
        msx.write_byte(0xE31B, 0xFF)
        time.sleep(2.0)

        print(f"\n=== Entity type probe (slot {PROBE_SLOT}, addr 0x{PROBE_ADDR:04X}) ===\n")

        for typ in TARGETS:
            # Refresh player invincibility each probe
            msx.write_byte(0xE305, msx.read_byte(0xE305) | 0x80)
            msx.write_byte(0xE31B, 0xFF)

            slot = probe_type(msx, typ)
            print(f"── Type {typ:2d} (0x{typ:02X}) ──")
            print(fmt_slot(slot, PROBE_ADDR))
            print()


if __name__ == "__main__":
    main()
