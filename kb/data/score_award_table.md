---
address: 0x4AEA
end: 0x4B29
kind: data
name: score_award_table
confidence: confirmed
sprint: "0047"
tags: [score, bcd, hud]
---

# score_award_table

## Summary
Table of **3-byte BCD point values** (little-endian: lo, mid, hi), indexed by an
award index `× 3`. `add_score` (0x4A74) reads `0x4AEA + index*3` and BCD-adds the
value to the player score; a second site (0x91B9) reads `0x4AEA + index*3 + 2`
(the hi byte) to render an award value via `render_score_bcd`.

> The CLAUDE.md DB tracker previously guessed this region (0x4AEA–0x4B83) was
> "HUD digit/BCD glyph data". It is not glyph data — score digits use the font
> tiles (0x30+digit) directly. This is the score-award value table.

## Entries (BCD points, ascending)

| idx | bytes (lo mid hi) | points |
|-----|-------------------|--------|
| 0 | 00 00 00 | 0 |
| 1 | 01 00 00 | 1 |
| 2 | 06 00 00 | 6 |
| 3 | 10 00 00 | 10 |
| 4 | 17 00 00 | 17 |
| 5 | 20 00 00 | 20 |
| 6 | 30 00 00 | 30 |
| 7 | 50 00 00 | 50 |
| 8 | 80 00 00 | 80 |
| 9 | 00 01 00 | 100 |
| 10 | 00 02 00 | 200 |
| 11 | 00 04 00 | 400 |
| 12 | 00 08 00 | 800 |
| 13 | 00 10 00 | 1000 |
| 14 | 00 15 00 | 1500 |
| 15 | 00 20 00 | 2000 |
| 16 | 00 30 00 | 3000 |
| 17 | 00 40 00 | 4000 |
| 18 | 00 50 00 | 5000 |
| 19 | 00 00 01 | 10000 |
| 20 | 00 20 00 | (2000, repeat) |

(~21 entries; the exact upper bound depends on the maximum award index used.)

## Live confirmation (sprint 0047)
`add_score(idx)` from score 0 produced exactly `table[idx]` for idx 1/9/13
(1 / 100 / 1000 points), values read directly from ROM. `tools/sprint0047_verify.py`.

## Adjacent table (0x4B2A, `data_4b2a`)
The bytes at **0x4B2A–0x4B82** are a *separate* table (small values 0x00–0x13,
with non-BCD bytes like 0x0F) with no direct reference found in the
disassembly — **not** part of the score-award table and not HUD render data;
likely difficulty/ALC parameters (candidate [[I-alc-adaptive-difficulty]]),
tracked there, out of subsystem N scope.

## See also
- `add_score.md` (0x4A74), `render_score_bcd.md` (0x49B5).
