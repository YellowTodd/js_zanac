"""
Generate scripts/no_enemies.ips

Strategy: redirect all enemy entity handlers in the jump table to entity_clear
(0x48D0), so any spawned enemy slot is zeroed out on its first dispatch.

Kept intact:
  type  1 (0x30B9): player ship       -> 0x75D5
  type  2 (0x30BB): player shot       -> 0x7221
  type  3 (0x30BD): fire weapon       -> 0x7253
  type 60 (0x312F): death explosion   -> 0x869E  (respawn flow stability)
  type 63 (0x3135): player-respawn    -> 0x78AF  (respawn flow stability)

Redirected to entity_clear 0x48D0 (LE: D0 48):
  types  4-59 : ROM offsets 0x30BF-0x312E  (112 bytes, 56 entries)
  types 61-62 : ROM offsets 0x3131-0x3134  (  4 bytes,  2 entries)
  types 64-89 : ROM offsets 0x3137-0x316A  ( 52 bytes, 26 entries)
"""

import struct
import pathlib

ROM_BASE  = 0x4000          # ROM mapped at 0x4000 in MSX address space
ECLEAR_LO = 0xD0            # entity_clear = 0x48D0
ECLEAR_HI = 0x48

def rom_off(addr: int) -> int:
    return addr - ROM_BASE

def make_ips(segments: list[tuple[int, bytes]]) -> bytes:
    buf = bytearray(b"PATCH")
    for offset, data in segments:
        assert offset != 0x454F4F, "IPS offset collision with EOF marker"
        buf += struct.pack(">I", offset)[1:]    # 3-byte BE
        buf += struct.pack(">H", len(data))     # 2-byte BE size
        buf += data
    buf += b"EOF"
    return bytes(buf)

PAIR = bytes([ECLEAR_LO, ECLEAR_HI])

segments = [
    # types 4-59 (56 entries = 112 bytes)
    (rom_off(0x70BF), PAIR * 56),
    # types 61-62 (2 entries = 4 bytes)
    (rom_off(0x7131), PAIR * 2),
    # types 64-89 (26 entries = 52 bytes)
    (rom_off(0x7137), PAIR * 26),
]

ips = make_ips(segments)

out = pathlib.Path(__file__).parent.parent / "scripts" / "no_enemies.ips"
out.write_bytes(ips)
print(f"Written {len(ips)} bytes -> {out}")

# Verification: apply the patch to a ROM copy and check key entries
rom_path = pathlib.Path(__file__).parent.parent / "source" / "zanac.rom"
rom = bytearray(rom_path.read_bytes())
for offset, data in segments:
    rom[offset:offset + len(data)] = data

def check(t, expected_handler):
    off = rom_off(0x70B9) + (t - 1) * 2
    actual = rom[off] | (rom[off + 1] << 8)
    ok = "OK" if actual == expected_handler else f"FAIL (got 0x{actual:04X})"
    print(f"  type {t:2d}: 0x{actual:04X}  {ok}")

print("Kept entries:")
for t, h in [(1, 0x75D5), (2, 0x7221), (3, 0x7253), (60, 0x869E), (63, 0x78AF)]:
    check(t, h)

print("Enemy entries (should all be 0x48D0):")
for t in [4, 10, 20, 35, 59, 61, 64, 80, 89]:
    check(t, 0x48D0)
