---
letter: L
title: Ending & Credits
coverage: done
status: done
---

# L — Ending & Credits

## Role

The post-game-beaten sequence: the ending setup (music, graphics, enemy-state
reset) and the staff-credits / roll display (centered names from a script,
fire-to-cycle, ESC-to-title). Triggered by [[K-game-flow-state-machine]] via
E102 bit 3; runs over a continuing scroll from [[D-scroll-and-tile-rendering]].

## Key routines

| Addr | Name | Conf | Notes |
|------|------|------|-------|
| 0x46D9 | `credits_display` | confirmed | staff-roll entry + page loop |
| 0x4ACE | `compare_save_hiscore` | confirmed | promote score → top score on game-end |
| 0x91FD | `ending_setup` | confirmed | ending init (music/gfx/enemy reset) |
| 0x9433 | `init_credits_stream` | confirmed | load credits scroll stream |
| 0x92CA | `clear_credits_busy` | confirmed | clears credits busy flag |

## Data

- Credits script + string tables at **0x4775–0x4897** (kept as DB; described in
  `credits_display`).

## Guides

- `input-state-machine` (§ end-credits sequence).

## Gaps / open questions

None — all L routines `confirmed` (sprint 0046). `credits_display` and
`init_credits_stream` are live-confirmed; `compare_save_hiscore` (0x4ACE) now has
its own entry. The VRAM text-placement helpers (`tile_to_vram_addr` 0x5BDD,
`vdp_write_byte_di` 0x5BFC) are confirmed under [[B-frame-render-pipeline]].

## Sprints

0033 (credits setup), 0046 (confirm credits_display / init_credits_stream,
add `compare_save_hiscore`).
