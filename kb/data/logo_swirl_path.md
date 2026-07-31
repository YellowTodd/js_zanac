---
address: 0x5B59
end: 0x5B90
kind: data
name: logo_swirl_path
confidence: confirmed
sprint: "0042"
tags: [title-screen, animation, table]
---

# logo_swirl_path

## Summary

The flight path for the title-screen logo swirl: **28 entries** (`0x1C`), 2 bytes
each = `(row, col)` in name-table cells, read by `lookup_swirl_coord` (0x5B91)
and consumed by the title animation loop in `title_intro_seq`. Index **0x1B** is
the off-screen entry point (bottom-right); index **0** is the logo's home
position near the screen centre. Each logo row walks its countdown down through
this table, so the rows spiral in and land.

## Layout

`0x5B59`, 56 bytes, two bytes per step: **byte 0 = column, byte 1 = row**.

`lookup_swirl_coord` does `LD D,(HL); INC HL; LD E,(HL); EX DE,HL`, so byte 0
lands in `H` and byte 1 in `L`; `tile_to_vram_addr` (0x5BDD) then computes
`0x3800 + L×32 + H`, making `L` the row and `H` the column. An earlier note here
had the two swapped ("byte 0 = row `L`"); the table below was already right.
Entry 0 is (col 7, row 5), which is where the logo lands — matching the
"logo tiles, rows 5–9" capture in [[zanac-vdp-layout]].

| idx | col,row | idx | col,row | idx | col,row | idx | col,row |
|----|---------|----|---------|----|---------|----|---------|
| 00 | 5,7  | 07 | 5,13 | 0E | 1,7  | 15 | 17,8  |
| 01 | 6,7  | 08 | 4,13 | 0F | 2,5  | 16 | 19,11 |
| 02 | 7,8  | 09 | 3,13 | 10 | 4,3  | 17 | 20,15 |
| 03 | 7,9  | 0A | 2,12 | 11 | 6,3  | 18 | 21,19 |
| 04 | 7,10 | 0B | 1,11 | 12 | 8,3  | 19 | 21,23 |
| 05 | 7,11 | 0C | 1,10 | 13 | 11,3 | 1A | 21,24 |
| 06 | 6,12 | 0D | 1,9  | 14 | 14,5 | 1B | 21,31 |

Plotting the points traces a spiral: in from the bottom-right (idx 0x1B), looping
up and around to settle at (col 5–7, row 7–11) — the logo block.

## Notes

- A logo row is drawn at `path[countdown]` with the row index (0–4) added to the
  row coordinate, so the five rows stack at home rows 7..11.
- Represented in `zanac.asm` as a `DB` block under the `logo_swirl_path:` label
  (sprint 0042 converted it from the disassembler's earlier bogus instruction
  decode; the adjacent `draw_title_text` inline strings were de-tangled at the
  same time). ROM byte-identical.

## Consumed by

`lookup_swirl_coord` (0x5B91) → `draw_logo_row` (0x5BA0), driven by the animation
loop in `title_intro_seq` (0x5A4A–0x5AC7).
