---
address: 0x7b7b
end: 0x7bea
kind: data
name: teruzo_motion_tables
confidence: confirmed
sprint: "0049"
tags: [entity, enemy, teruzo, motion-script]
---

# teruzo_motion_tables

Spawn-point + flight-script data for the teruzo (types 12–15), consumed by
[[handler_type12_teruzo]] (0x7b07). The handler indexes a pointer table at
**virtual base 0x7b63** with `((type & 0xFE) + random_bit) × 2`; for types 12–15
that lands on the four live pointers at 0x7b7b–0x7b82.

## Pointer table (0x7b7b–0x7b82, 4 × LE)

| Index | Addr | → block | Used by |
|-------|------|---------|---------|
| 0x18 | 0x7b7b | 0x7b83 | type 12/13, rnd=0 |
| 0x1a | 0x7b7d | 0x7b98 | type 12/13, rnd=1 |
| 0x1c | 0x7b7f | 0x7bae | type 14/15, rnd=0 |
| 0x1e | 0x7b81 | 0x7bcc | type 14/15, rnd=1 |

## Script blocks

Each block = `Y, X, colour` then a list of 16-direction indices (0=down, 4=right,
8=up, 0xC=left; same convention as [[vel_dir_table]] / 0x4cf7). One index is
applied every 8 frames; a byte with **bit 7 set** is terminal (held forever).

| Block | Spawn (Y,X) | Colour | Corner | Direction script (bit7 = hold) |
|-------|-------------|--------|--------|--------------------------------|
| 0x7b83 | 112, 208 | 0x8A | lower-right | 08×4, 07,06,05,04,03,02,01,00, 0F,0E,0D,0C, 0B, **8A**(→0A) |
| 0x7b98 | 112, 16  | 0x8A | lower-left  | 00×5, 01,02,…,0D, **8E**(→0E) |
| 0x7bae | 32, 208  | 0x89 | upper-right | 06×12, 04,02,00, 0E×8, 0D,0C,0B, **8A**(→0A) |
| 0x7bcc | 32, 16   | 0x89 | upper-left  | 00, 02×12, 04,06,08, 0A×8, 0B,0C,0D, **8E**(→0E) |

The two lower blocks (0x8A) enter from the bottom corners arcing upward; the two
upper blocks (0x89) enter from the top corners arcing across. The terminal
direction sends each off the far edge.

## Source note

Labelled `DB` block `teruzo_motion_tables:` in source (sprint 0053; was
mis-decoded as instructions). No `DD` absorption — the table's last byte decoded
as a 1-byte op, so the luster entry 0x7beb was already correct.
