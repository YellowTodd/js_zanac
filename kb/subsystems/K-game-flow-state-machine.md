---
letter: K
title: Game-Flow State Machine
coverage: done
status: done
---

# K — Game-Flow State Machine

## Role

The glue that sequences the high-level states — title → play → player-hit →
game-over → (credits) → title — and owns the master game-state block, lives,
round/level counters, score, and the E102 state/flag bits read each frame.
Drives [[B-frame-render-pipeline]]'s `gameplay_frame_loop`, dispatches
[[F-player-ship-and-weapons]] death and [[L-ending-and-credits]], and reads
input (see `input-state-machine`).

## Key routines

| Addr | Name | Conf | Notes |
|------|------|------|-------|
| 0x4042 | `main_game_loop` | confirmed | top of the play state; branches on E102 each frame |
| 0x40DA | `level_complete_handler` | confirmed | stage clear / transition; advances round via `resolve_round_from_ptr` |
| 0x4663 | `game_over_handler` | confirmed | last-life → game over; sets E102 bit 7 + "GAME OVER" |
| 0x46A8 | `wait_fire_or_timeout` | confirmed | timed wait with fire abort |
| 0x9444 | `resolve_round_from_ptr` | confirmed | stream pointer (E722) → round number → E701 |

## State (0xE100 block)

| Addr | Name | | Addr | Name |
|------|------|-|------|------|
| 0xE100 | `input_state` (not phase) | | 0xE10B | `shot_level` |
| 0xE102 | `status_flags` (E102 flag byte) | | 0xE10A | `lives` |
| 0xE103/04/05 | `score_lo/mid/hi` | | 0xE106/07/08 | `topscore_lo/mid/hi` |
| **0xE701** | **`round` (1–8, 0=ending)** — scroll-state block | | 0xE110 | `shot_state` (NOT round) |

E102 flag bits (full map in `input-state-machine`): 0 player_hit, 1 game_over,
2 scroll, 3 end_credits, 4 display_timer, 5 level_complete, 6 respawn,
7 go_to_title. The **round** lives in `E701`, not `E110` (corrected sprint 0045).

## Guides

- `input-state-machine` (full E102 map + per-state keys), `round-progression`
  (round advance + end-of-game), `keyboard-input`, `game_state_block` (data),
  `stage_stream_ptr_table` (data).

## Gaps / open questions

None — all K routines `confirmed` (sprint 0045). The E102 bit map is fully
enumerated and confirmed (`input-state-machine`), round progression is traced
end-to-end (`round-progression`): round = `E701`, advanced by
`resolve_round_from_ptr`; after round 8 the ending pointer 0xA6F4 → `E701=0` →
credits → title, with **no second loop**.

## Sprints

Done: 0027 (game state block), 0032 (gameplay key handling), 0034 (main game loop),
0045 (flag map + round progression; corrected E110→E701, added
`resolve_round_from_ptr` / `stage_stream_ptr_table`).
**Note:** the STOP-pause routine `pause_frame_tick` (0x4E0B) is owned by
[[N-hud-and-status-display]] (sprint 0036); the pause *state machine* is already
confirmed in `input-state-machine`.
