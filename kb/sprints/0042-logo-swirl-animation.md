---
id: "0042"
status: done
range: 0x5A4A-0x5AC7,0x5AC8-0x5AF7,0x5B59-0x5B90,0x5B91-0x5B9F,0x5BA0-0x5BDC,0x4827-0x48A4
strategy: subsystem_slice
budget_turns: 25
subsystems: [J]
---

# Sprint 0042 — Title logo swirl animation (J follow-up)

## Goal

Document the previously-uncharacterised internals of the title logo animation in
`title_intro_seq` (the swirl-in of the Zanac logo), and fix two mislabels in the
existing entry.

## What the animation does (from the user + code)

When the title screen loads, all text (top-score/score labels, "GAME DESIGNED BY
COMPILE", "PRODUCED BY…", copyright) is drawn first. Then the Zanac logo enters
as **5 independent horizontal rows** that fly in along a **swirl/spiral path**
and converge to their home position near the screen centre (name-table rows 7–11).

## Mechanism

- Five rows, seeded with staggered countdowns `0xE1FA..0xE1FE = 1C 20 24 28 2C`
  (base 0x1C, step 4); `0xE1F9` is the current row index (0–4) within a pass.
- Each frame the loop decrements every row's countdown; while a row's countdown
  is in `[0,0x1B]` it is drawn at `logo_swirl_path[countdown]`, offset vertically
  by the row index. When a countdown reaches 0 the row is home; when all five are
  home (`C==5`) the loop ends. `sub_46bc` (start key) aborts early.
- `logo_swirl_path` (**0x5B59**, 28 × `col,row`) is the trajectory: index 0x1B =
  off-screen bottom-right → index 0 = logo home (~col5/row7). A real spiral.
- `lookup_swirl_coord` (**0x5B91**) returns `HL = path[countdown]`.
- `draw_logo_row` (**0x5BA0**) blits one logo row: up to 18 tile-names from
  `logo_tile_rows` (**0x4827** + 25×row) to the name table at the swirl coord
  via `tile_to_vram_addr`/`SETWRT`, **clipping the width when the row runs off
  the right edge** (col ≥ 14 ⇒ count = 0x20 − col).
- `draw_title_text` (**0x5AC8**) redraws the credit text lines ("GAME DESIGNED BY
  COMPILE" @0x39E3, "PRODUCED BY…", …) via the inline-string `vdp_set_addr_write`
  helper.

## Corrections to `title_intro_seq.md`

- `sub_5BA0` was labelled "PSG-channel tick (sound engine)" — **wrong**; it is the
  logo-row tile blitter (`draw_logo_row`).
- `sub_5AC8` was labelled "frame sync / wait VBlank" — **wrong**; it draws the
  credit text. The actual per-pass frame wait is `wait_frames` (`sub_5BEC`, B=2)
  at 0x5AAB.
- "scrolling positions / single blit" reworded to the swirl-in of 5 rows.

## Notes / follow-ups

- `0x5B59–0x5B90` (the swirl table) **converted to a `DB` block** in `zanac.asm`.
  Doing so required de-tangling the adjacent `draw_title_text` body (0x5AC8–0x5B58):
  its inline credit strings were mis-decoded as instructions, and the bogus `JR`s
  they produced were the only references to the swirl table's fake labels. The
  whole region was regenerated as real instructions + `DB` strings + the `DB`
  table (153 mis-decoded lines → 25 clean lines), recovering the title text
  ("GAME DESIGNED BY COMPILE", "PRESENTED … BY PONY INC.", "COPYRIGHT @ 1986 PONY
  INC."). `redisasm verify` byte-identical; tabs/indentation preserved.
- `logo_tile_rows` at 0x4827 lives inside the 0x4775–0x4897 block (shared with the
  credits script data); the 5th row is mostly blank and its 25-byte slot tail
  overlaps the start of `entity_update` (0x4898), so only ~4 rows carry real tiles.
- `0x5C28` is an alternate entry of `vdp_set_addr_write` (skips `vdp_int_disable`).

## Verification

`redisasm verify` byte-identical after label adds; `zanackb validate` 0 errors.
