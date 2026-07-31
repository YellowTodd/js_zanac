---
letter: N
title: HUD & Status Display
coverage: done
status: done
---

# N — HUD & Status Display

## Role

The on-screen readouts: score and top-score (BCD), remaining lives, and the
status bar showing the current `fire` number and its limit. Renders into the
VRAM name table each frame; values come from [[K-game-flow-state-machine]]
(score/lives) and [[F-player-ship-and-weapons]] (fire weapon).

> Note: this subsystem was added after the initial A–M proposal (the score/HUD
> rendering in `0x4900-hud/` had no letter); it is its own concern.

## Key routines

| Addr | Name | Conf | Notes |
|------|------|------|-------|
| 0x4996 | `render_lives_score` | confirmed | score→0x3809, topscore→0x3815 |
| 0x49A7 | `render_topscore_row2` | confirmed | topscore→0x38B8 |
| 0x49AF | `render_score_row2` | confirmed | score→0x3918 |
| 0x49B5 | `render_score_bcd` | confirmed | 3-byte BCD → 6 digit tiles (helper 0x49DD) |
| 0x4A74 | `add_score` | confirmed | BCD-add `score_award_table[idx]` to score |
| 0x4AA5 | `score_display_update` | confirmed | per-frame new-top-score flash (E114 bit6) |
| 0x4B83 | `write_digit_to_vram` | confirmed | 2-digit decimal (3-digit entry 0x4B8D) |
| 0x4BD4 | `draw_hud_labels` | confirmed | static labels at screen init (helper 0x4BC7) |
| 0x4C4D | `update_status_bar` | confirmed | round + level + lives |
| 0x4C68 | `render_round_digit` | confirmed | round (E701) → 0x3A1B (was mis-named render_hiscore_digit) |
| 0x4C74 | `render_hex_byte` | confirmed | 2 hex digits (shared — ALC display [[I-alc-adaptive-difficulty]]) |

## Data

- score/topscore BCD at 0xE103–0xE108; `score_award_table` (0x4AEA).
- Digit glyphs are the **font tiles** (`0x30 + digit`, `0x20` for a leading-zero
  space) — there is no separate HUD glyph table.

## Notes

- The **FIRE** readout value is rendered by the fire-weapon handler (≈0x730B,
  [[F-player-ship-and-weapons]]) using N's digit primitives, not a dedicated N
  routine. `0x4DA5` is the STOP-key `pause_handler` (K/input, sprint 0032) — it
  was mistakenly listed here as "update_fire_display"; removed.
- VRAM HUD targets: score 0x3809 / row2 0x3918, top 0x3815 / row2 0x38B8,
  level 0x39BB, lives 0x397A, round 0x3A1B.

## Gaps / open questions

None — all N render routines `confirmed` (sprint 0047). The 0x4AEA block is the
`score_award_table` (not glyph data); the adjacent `data_4b2a` (0x4B2A–0x4B82)
is a separate unreferenced table, likely ALC params, tracked under
[[I-alc-adaptive-difficulty]].

## Sprints

Done: 0032 (per-frame score/pause), 0046 (`compare_save_hiscore`),
0047 (confirm all render routines; `render_hex_byte`, `draw_hud_labels`,
`add_score`, `score_award_table`; renamed `render_round_digit`).
Sprint 0036's N items (hex formatter 0x4C74, 0x4AEA block) are resolved here.
