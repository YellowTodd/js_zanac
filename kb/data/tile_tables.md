---
address: 0xA444
end: 0xA653
kind: data
name: tile_tables
confidence: confirmed
sprint: "0037"
tags: [scroll, tile, level-map, base-layer]
---

# Per-stage tile-block tables (base layer)

Decoded sprint 0029 from `sub_9888` (0x9888) index math. These are **not**
1-byte palette selectors — each entry is a **24-byte vertical tile-column
block** (24 = on-screen tile rows; `scroll_row` 0xE714 wraps 23→0). `sub_9888`
computes per-stage pointers into them at level setup and stores them at
0xE2AE / 0xE2B0 / 0xE2B2; the scroll engine LDIRs columns from these into the
assembled tile row.

| Table  | Range          | Entries | Index | Stride | Stored to |
|--------|----------------|---------|-------|--------|-----------|
| 0xA444 | 0xA444–0xA4A3  | 4       | `stage & 3` | 24 (0x18) | 0xE2AE (primary) |
| 0xA4A4 | 0xA4A4–0xA563  | 8       | `stage & 7` | 24 (0x18) | 0xE2B0 (variant A) |
| 0xA564 | 0xA564–0xA623  | 8       | `stage & 7` | 24 (0x18) | 0xE2B2 (variant B) |
| 0xA624 | 0xA624–0xA63B  | 1       | fixed | 24 (0x18) | 0xE2B4 |
| 0xA63C | 0xA63C–0xA653  | 1       | fixed | 24 (0x18) | 0xE2B6 |

The last two are two **fixed** (non-stage-indexed) 24-byte tile columns loaded
once at level init: `sub_4236` does `LD HL,0xA624; LD (0xE2B4),HL` and
`LD HL,0xA63C; LD (0xE2B6),HL` (0x4236/0x423C). They extend the pointer triplet
(0xE2AE/0xE2B0/0xE2B2) with two more selectable tile-column sources for the
column-group `param` byte. A short tile strip `6F 70 71 72 1D 72 7B 7C`
occupies the 8-byte tail 0xA654–0xA65B before the first map script (0xA65C).

`stage` = `(0xE702) & 7` (level_row_ctr low bits select the visual theme; the
0xA444 primary table uses only `& 3`). Pointer setup in `sub_9888`:

```
9888  A = (0xE702)&3; A = A*24; (0xE2AE) = 0xA444 + A     ; primary block
989e  A = (0xE702)&7; HL = A*24; (0xE2B0) = 0xA4A4 + HL   ; variant A
                                 (0xE2B2) = 0xA564 + HL   ; variant B
```

## Contents

Each byte is an 8×8 tile (name-table character) ID. Values cluster around
0x28/0x29 (primary fill tiles) and 0x17–0x19 / 0x24–0x27 (variant detail
tiles), consistent with a tiled starfield/terrain background.

```
A444 (primary, entry 0):  9A 17 17 8B 02 02 8C 8B 28 28 28 29 28 28 28 29
                          28 28 28 28 28 29 28 28
A4A4 (variant A, entry 0):28 29 28 28 28 28 28 28 17 17 18 18 18 18 18 17
                          18 17 17 18 17 17 18 17
A564 (variant B, entry 0):17 17 17 17 17 18 18 19 27 27 27 27 26 26 27 26
                          26 27 26 26 24 27 26 27
```

The `param` byte of a map-script column-group spec (command 0x2) and the
`(IY+1)` slot byte select, via bits 4–6, which of the pointer triplet
(0xE2AC/0xE2AE/0xE2B0/0xE2B2) supplies the tile column for a given group, and
bit 7 / bit 3 add octave-like offsets (+0x17 / +0x2E) to the tile IDs in
`scroll_map_reader` (0x9986). See `kb/symbols/0x9000-scroll/scroll_map_reader.md`.
