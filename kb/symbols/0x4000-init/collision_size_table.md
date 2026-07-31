---
address: 0x45C9
end: 0x4648
kind: data
name: collision_size_table
confidence: confirmed
sprint: "0030"
tags: [collision, entity, sprite]
---

# collision_size_table

## Summary

**128-byte** table of hitbox insets, read in **pairs** by the collision routines
at 0x4560 and 0x45A0. Indexed by `SAT_NAME >> 1`; the byte at that index is the
**Y inset** and the next byte is the **X inset**.

They are **insets, not half-sizes**: 0x45B1 computes `B = Y + inset` and 0x45B4
computes `C = Y + 0x10 - inset`, i.e. the nominal 16x16 cell shrunk by `inset`
on each side. A value of 0 therefore means the *full* 16 pixels on that axis,
not "no collision".

### Extent corrected (2026-07-30)

The entry said 32 bytes (0x45C9-0x45E8). Sprite names run to 0xFF, so the index
`N >> 1` reaches 0x7F and the table must cover **0x45C9-0x4648** - 128 bytes,
ending exactly where [[player_hit_handler]] begins at 0x4649. The bytes in
between are all small (0-7) inset values, and the disassembly renders every one
of them as an instruction (`NOP`, `INC BC`, `LD B,C`, ...), which is why they
were being dropped from the web port's data image.

### Values that matter most

| sprite | index | Y inset | X inset | box |
|--------|-------|---------|---------|-----|
| 0x20 player ship | 0x10 | 1 | 1 | 14x14 |
| 0x24 ground structure | 0x12 | 0 | 0 | full 16x16 |
| 0x28 player shot | 0x14 | 0 | 6 | 16 tall, **4 wide** |
| 0x2C box | 0x16 | 0 | 3 | 16x10 |

**Updated in sprint 0030:** sprint 0018 documented only single "radius" values.
The full decode of 0x4560 / 0x45A0 shows the table is read as consecutive pairs:
`E ← table[idx]` (Y), then `INC HL; E ← (HL)` (X).

## Encoding

For an entity with `sat_name = N`:
- Y hitbox half-size = `table[N >> 1]`
- X hitbox half-size = `table[(N >> 1) + 1]`

Adjacent SAT_NAME values (e.g. 0x04 and 0x05) share the same Y-size index but
produce different X-size reads (offset by 1). This means the table encodes Y and
X sizes interleaved rather than as independent per-sprite pairs.

## Table (SAT_NAME index pairs → Y size / X size)

| idx | SAT_NAME range | Y size | X size | Sprite |
|-----|---------------|--------|--------|--------|
| 0 | 0x00–0x01 | 0 | 0 | pat0 power_chip — no collision |
| 2 | 0x04–0x05 | 3 | 3 | pat1 comet |
| 4 | 0x08–0x09 | 0 | 0 | pat2 |
| 6 | 0x0C–0x0D | 0 | 0 | pat3 |
| 8 | 0x10–0x11 | 0 | 0 | pat4 |
| 10 | 0x14–0x15 | 3 | 3 | pat5 small_star |
| 12 | 0x18–0x19 | 5 | 0 | pat6 light_bar — Y-only hitbox |
| 14 | 0x1C–0x1D | 6 | 6 | pat7 lead — largest hitbox |
| 16 | 0x20–0x21 | 1 | 1 | pat8 med_circle |
| 18 | 0x24–0x25 | 0 | 0 | pat9 |
| 20 | 0x28–0x29 | 0 | 6 | — |
| 22 | 0x2C–0x2D | 0 | 3 | — |
| 24 | 0x30–0x31 | 0 | 0 | — |
| 26 | 0x34–0x35 | 2 | 2 | pat13 super_hard_bolt |
| 28 | 0x38–0x39 | 4 | 4 | pat14 player_ship |
| 30 | 0x3C–0x3D | 4 | 4 | pat14 player_ship (high SAT_NAME) |

Raw bytes: `00 00 03 03 00 00 00 00 00 00 03 03 05 00 06 06 01 01 00 00 00 06 00 03 00 00 02 02 04 04 04 04`
