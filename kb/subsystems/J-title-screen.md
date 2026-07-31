---
letter: J
title: Title Screen
coverage: complete
status: done
---

# J — Title Screen

## Role

The power-on attract sequence: company names + 1986, the animated Zanac logo
entering while the title music plays, then the idle state waiting for SPACE to
start. Shares graphics loading with [[E-level-data-and-decompression]], music
with the sound system, and hands off to [[K-game-flow-state-machine]] on start.
The ESC-on-title secret belongs to [[M-secrets-and-warps]].

## Key routines

| Addr | Name | Conf | Notes |
|------|------|------|-------|
| 0x41BA | `display_timer_countdown` | confirmed | attract/idle timing |
| 0x41CB | `clear_title_state` | confirmed | reset title vars |
| 0x41DB | `title_screen_init` | confirmed | set up the title screen |
| 0x43D2 | `check_esc_key` | confirmed | reads ESC (row 7 bit 2); ESC held at start ⇒ continue from last round (E701 not reset) |
| 0x5A11 | `title_intro_seq` | confirmed | logo-swirl animation driver; start key via `sub_46bc` |
| 0x5C3C | `load_logo_tiles` | confirmed | decompress logo tiles into VRAM |
| 0x5B91 | `lookup_swirl_coord` | confirmed | read `logo_swirl_path[step]` → (row,col) |
| 0x5BA0 | `draw_logo_row` | confirmed | blit one logo row at the swirl coord (right-edge clipped) |
| 0x5AC8 | `draw_title_text` | confirmed | draw credit text ("GAME DESIGNED BY COMPILE", …) |
| 0x5C25 | `vdp_set_addr_write` | confirmed | inline-string → name table (alt entry 0x5C28) |

The actual **start** key (SPACE/SHIFT/Z/joystick) is read by `sub_46bc` inside
the `title_intro_seq` loop, not by `check_esc_key`.

## Data

- `gfx_logo_bitmap` (0x5D2C), `gfx_logo_colors` (0x5EF0).
- `logo_swirl_path` (0x5B59) — 28-step (row,col) swirl trajectory.
- `logo_tile_rows` (0x4827) — 5 rows of logo tile-names (stride 25).

## Status: fully documented ✓ (sprints 0041 + 0042)

All routines are `confirmed`. `check_esc_key` (0x43D2) was live-confirmed in 0041
(keymatrix row 7 `0xFF`→`0xFB` ⇒ **ESC = row 7 bit 2**; renamed from the
misleading `check_start_key`; `title_screen_init` branch corrected — ESC-held ⇒
skip `E701=1` ⇒ continue/secret round).

The **logo swirl** internals were documented in 0042: the logo flies in as 5
independent rows (`logo_tile_rows` 0x4827) along a 28-step spiral
(`logo_swirl_path` 0x5B59), via `lookup_swirl_coord` + `draw_logo_row`, with the
credit text drawn by `draw_title_text`. Two old mislabels were fixed
(`draw_logo_row` was "PSG tick", `draw_title_text` was "frame sync"). State:
`0xE1F9` (row index), `0xE1FA..E1FE` (five staggered countdowns).

The asm was also cleaned up: `logo_swirl_path` (0x5B59–0x5B90) is now a proper
`DB` block and the adjacent `draw_title_text` inline strings (the title credit
lines) were de-tangled from their bogus instruction decode — ROM byte-identical.

## Sprints

Done: 0019 (title screen internals), 0041 (`check_esc_key` confirm + rename),
0042 (logo swirl animation: code + data).
