---
address: 0x4827
end: 0x4897
kind: data
name: logo_tile_rows
confidence: confirmed
sprint: "0042"
tags: [title-screen, logo, tiles, name-table]
---

# logo_tile_rows

## Summary

The name-table tile-index strips for the Zanac title logo: **6 rows**, addressed
as `0x4827 + 19*row` (stride **19 decimal**), **18 tile-names** drawn per row by
`draw_logo_row` (0x5BA0). Rows 0–4 are the logo itself, tile indices 0xB0–0xE6 —
the patterns `load_logo_tiles` decompresses into VRAM tiles 176–236. **Row 5 is
18 spaces**: the blank strip the swirl's erase pass blits over a row's previous
position.

## Layout (as read from ROM, 18 bytes/row)

```
row 0 (0x4827): 20 B0 B1 B2 B3 B4 B5 B6 B7 B8 B9 BA BB BC B2 B2 BD 20
row 1 (0x483A): 20 20 20 BE BF C0 C1 C2 C3 C4 C5 C6 C7 C8 20 20 20 20
row 2 (0x484D): 20 20 C9 CA CB CC CD CE CF D0 D1 D2 D3 D4 20 20 20 20
row 3 (0x4860): 20 D5 D6 D7 D8 D9 DA DB DC DD DE D9 DF E0 D9 D9 E1 20
row 4 (0x4873): E2 E3 E4 E5 E5 E5 E5 E5 E5 E5 E5 E5 E5 E5 E5 E5 E5 E6
row 5 (0x4886): 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20
```

`0x20` = space (blank cell). Tiles run in unbroken ascending order 0xB0→0xE6
across rows 0–4, with 0xB2/0xD9/0xE5 deliberately repeated; rows 0–2 are the
white wordmark, row 3 its grey shading and row 4 the grey baseline bar.

## Stride correction (2026-07-30)

This entry previously recorded "stride 25 (`0x19`)" and a five-row layout —
a decimal/hex mix-up. The index math in `draw_logo_row` at 0x5BC3
(`4F 87 87 87 81 87 81` = `LD C,A; ADD A,A ×3; ADD A,C; ADD A,A; ADD A,C`)
computes x → 2x → 4x → 8x → 9x → 18x → **19x**, i.e. 19 decimal (`0x13`).

Three independent checks confirm 19:

- the table then ends exactly at 0x4897, one byte before `entity_update`
  (0x4898), instead of overrunning it;
- the logo tile indices form one unbroken 0xB0..0xE6 run, with every tile the
  graphics blocks define used exactly once;
- row 5 comes out as 18 spaces, which is what the erase pass at 0x5A66
  (`LD A,5`) needs — under stride 25 that read lands at 0x48A4, inside
  `entity_update`, and the animation blits instruction bytes as tiles.

Rendering the strips both ways settles it visually: stride 19 produces the ZANAC
wordmark, stride 25 produces disconnected fragments.

## Notes

- Lives inside the 0x4775–0x4897 DB block (shared with the credits script data);
  this is the logo half of that block, and it fills the block exactly.
- `draw_logo_row` clips the 18-tile count at the right screen edge
  (col ≥ 14 ⇒ count = 0x20 − col).

## Read by

`draw_logo_row` (0x5BA0), via `0x4827 + 19*logo_row`; the row index is 0–4 for
the logo rows (from `0xE1F9`) and a literal 5 for the erase pass.
