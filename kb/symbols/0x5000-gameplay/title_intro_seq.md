---
address: 0x5A11
end: 0x5AC7
kind: routine
name: title_intro_seq
confidence: confirmed
inputs: {}
outputs: {}
clobbers: [AF, BC, DE, HL, IX, IY]
calls:
  - 0x46BC
  - 0x5189
  - 0x5C3C
  - 0x5BEC
  - 0x42E2
  - 0x5C25
  - 0x5C28
  - 0x4996
  - 0x5B91
  - 0x5BA0
  - 0x5AC8
called_by: [0x4042]
tags: [title-screen, animation, audio, graphics]
sprint: "0042"
---

# title_intro_seq

## Summary
Runs the company-logo / title-screen intro sequence: starts title music, blits
the Zanac logo tiles into VRAM, shows the name-table text ("SCORE", "TOP"),
then loops through a tile-scrolling animation until a joystick button or SPACE
is pressed.

## Sequence (source lines 2053–2127)

1. **`CALL sub_46bc`** — initialises joystick interface (via sub_4343/GICINI) and
   reads current button state.
2. **`LD A, 3; CALL play_sound_event`** — starts title music (event index 3).
   This is the first PSG write of the session.
3. **`CALL load_logo_tiles` (0x5C3C)** — RLE-decompresses logo bitmap and color
   data into VRAM PGT/CT for all three screen thirds.
4. **`LD B, 2; CALL wait_frames` (0x5BEC)** — 2-frame blank while tiles settle.
5. **`CALL enable_display` (0x42E2)** — screen on.
6. **`LD HL,0x3803; CALL vdp_set_addr_write` + inline "SCORE\0"`** — writes "SCORE"
   into the name table at row 0, col 3.
7. **`LD HL,0x3811; CALL 0x5C28` + inline "TOP\0"`** — writes "TOP" at row 0,
   col 17 (0x5C28 is the alt entry of `vdp_set_addr_write`). The bytes after each
   CALL are inline string data, not opcodes.
8. **`CALL sub_4996`** — clears the HUD/score row.
9. **Swirl init** (0x5A3D–0x5A48): `B=5, A=0x1C`; seed the five logo-row
   countdowns `0xE1FA..0xE1FE = 1C 20 24 28 2C` (base 0x1C, step 4).

### Logo-swirl loop (LAB_5A4A–LAB_5AC7)
The Zanac logo flies in as **5 independent horizontal rows** that follow a spiral
path and land at the centre. Each iteration runs **two passes** over the rows:

- `CALL sub_46bc; RET C` — abort if the start key is pressed.
- **Erase pass** (0x5A4E–0x5A74). For each of the 5 rows (`0xE1F9` = row index
  0–4): if its countdown is in `[1,0x1B]`, `lookup_swirl_coord` (0x5B91) reads
  `logo_swirl_path[countdown]`, the row index is added to the row coordinate,
  and `draw_logo_row` is called with **`A = 5`** (0x5A66) — strip 5 of
  [[logo_tile_rows]], which is 18 spaces. This blanks the position the row
  currently occupies.
- `CALL draw_title_text` (0x5AC8) — (re)draws the credit text lines.
- **Advance pass** (0x5A79–0x5AA7). Decrement every row's countdown (a row
  already at 0 stays there and bumps the done-counter `C`), then, for countdowns
  below `0x1B`, draw the row again at its **new** path position with
  **`A = 0xE1F9`** (0x5A96) — its own tile strip.
- `LD B,2; CALL wait_frames` (0x5BEC) — pace one step (~2 frames).
- Repeat until all 5 rows are home (`C==5`), then fall through to a wait that
  also exits on the start key.

> **Correction (2026-07-30).** This entry previously described a single pass
> that "blits that row's tile strip" for countdowns in `[1,0x1B]`. That is the
> *erase* pass, and it blits strip **5**, not the row's own strip — sprint 0042
> documented this animation statically and never covered the erase pass at all.
> The distinction only makes sense once [[logo_tile_rows]]' stride is read as 19
> rather than 25, which is what makes strip 5 a blank row instead of an overrun
> into `entity_update` code.

Staggered seeds (0x1C…0x2C) make the rows enter one after another; the shared
`logo_swirl_path` (index 0x1B off-screen → 0 home) gives the swirl.

## Logo rendering
The logo bitmaps are a **single blit** — `load_logo_tiles` writes all logo tiles
(0xB0–0xE6) into VRAM once. The *animation* moves the five name-table **rows**
(tile strips from `logo_tile_rows` 0x4827) along `logo_swirl_path`, not the
bitmaps. (Corrects an earlier note that mislabelled `sub_5BA0` as a PSG tick and
`sub_5AC8` as frame sync.)

## Entry/exit
- Called once per title-screen entry from `LAB_4042` (before `title_screen_init`).
- Returns normally; caller proceeds to `title_screen_init` (0x41DB).
