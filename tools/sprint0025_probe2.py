#!/usr/bin/env python3
"""Sprint 0025 probe — second batch.

Injects each target type into slot 24, runs one dispatch cycle, prints
the initialised slot. Special handling:
  - Type 63: injected with active flag already set (bit7-clear returns immediately)
  - Types 73–79: 0xE150 bit 1 set beforehand to unblock base-gated init
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
PROBE_SLOT = 24
PROBE_ADDR = ENT_BASE + PROBE_SLOT * SLOT_SIZE   # 0xE600

TARGETS = [7, 8, 9, 19, 20, 21, 26, 27, 30, 38, 40, 41, 46, 50, 56, 63, 68, 72, 73, 83]

# Types that need special injection flags or pre-conditions
ACTIVE_ON_INJECT   = {63}          # inject with bit7 set (handler ignores uninit)
BASE_GATE_TYPES    = set(range(73, 80))  # need 0xE150 bit1=1


def fmt_slot(slot: bytes) -> str:
    typ      = slot[0x00] & 0x7F
    active   = bool(slot[0x00] & 0x80)
    y, x     = slot[0x01], slot[0x02]
    sat_name = slot[0x03]
    sat_col  = slot[0x04]
    bflags   = slot[0x0C]
    vy_frac  = slot[0x08]
    vy       = slot[0x09]
    vx_frac  = slot[0x0A]
    vx       = slot[0x0B]
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
        f"  flags=0x{slot[0x00]:02X} active={active} type_after={typ}",
        f"  Y={y} X={x}",
        f"  sat_name=0x{sat_name:02X}→pat {pat}  sat_col=0x{sat_col:02X}",
        f"  bflags=0x{bflags:02X} (Y:{bflags&1} X:{(bflags>>1)&1}"
        f" anim:{(bflags>>2)&1} Yhom:{(bflags>>3)&1} Xhom:{(bflags>>4)&1})",
        f"  vy={vy} vy_frac=0x{vy_frac:02X}  vx={vx} vx_frac=0x{vx_frac:02X}",
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
    pers = " ".join(f"{slot[0x18+i]:02X}" for i in range(8))
    lines.append(f"  persist[18..1F]: {pers}")
    return "\n".join(lines)


def probe(msx, typ: int) -> bytes:
    msx.write_memory(PROBE_ADDR, bytes(SLOT_SIZE))
    msx.write_byte(PROBE_ADDR + 0x01, 100)
    msx.write_byte(PROBE_ADDR + 0x02, 120)
    inject_byte = (0x80 | typ) if typ in ACTIVE_ON_INJECT else typ
    msx.write_byte(PROBE_ADDR + 0x00, inject_byte)

    count_target = PROBE_SLOT + 2
    msx.cmd("set ::probe_n 0")
    bp = msx.cmd(
        f"debug set_bp 0x445F true "
        f"{{incr ::probe_n; if {{$::probe_n >= {count_target}}} "
        f"{{debug break}}}}"
    )
    msx.cont()
    time.sleep(1.0)
    msx.cmd(f"debug remove_bp {bp}")
    return bytes(msx.read_memory(PROBE_ADDR, SLOT_SIZE))


def main():
    with ZanacGame.launch(str(ROM)) as game:
        msx = game.client
        game.wait_for_title()
        game.start_game()
        msx.write_byte(0xE305, msx.read_byte(0xE305) | 0x80)
        msx.write_byte(0xE31B, 0xFF)
        time.sleep(2.0)

        print(f"\n=== Probe batch 2 (slot {PROBE_SLOT} / 0x{PROBE_ADDR:04X}) ===\n")

        for typ in TARGETS:
            msx.write_byte(0xE305, msx.read_byte(0xE305) | 0x80)
            msx.write_byte(0xE31B, 0xFF)

            # Base-gated types need 0xE150 bit 1 set
            if typ in BASE_GATE_TYPES:
                msx.write_byte(0xE150, msx.read_byte(0xE150) | 0x02)

            note = " [active-inject]" if typ in ACTIVE_ON_INJECT else ""
            note += " [base-gate unlocked]" if typ in BASE_GATE_TYPES else ""
            print(f"── Type {typ:2d} (0x{typ:02X}){note} ──")

            slot = probe(msx, typ)
            print(fmt_slot(slot))
            print()


if __name__ == "__main__":
    main()
