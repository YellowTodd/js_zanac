---
name: round-progression
description: "How Zanac advances through its 8 rounds: the E701 round selector, stage-clear transition via E722 + resolve_round_from_ptr, and the end-of-game (round 8 -> ending -> credits -> title) path. No second loop."
kind: guide
confidence: confirmed
sprint: "0045"
tags: [round, state-machine, level-transition, e102, e701, credits]
---

# Round progression

Zanac has **8 rounds** (plus a "secret"/ending round 0). The current round is
held in **`E701`** (in the scroll-state block at 0xE700), **not** in `E110`.

> Correction (sprint 0045): `game_state_block` previously labelled `E110` as the
> round (1–8). Live warp tests show `E701` tracks the round (warp r1/r3/r8 →
> E701 = 1/3/8) while `E110` stays `0x01` regardless. `E110` is a shot/fire-state
> byte written by the shot handler at 0x7684, not the round.

## Choosing the starting round

At game start `title_screen_init` reads `E701` (set to the chosen round; warps
patch it directly) and indexes `stage_stream_ptr_table` (0x945C) by `8 − E701`
to load that round's level stream. Holding **ESC** on the title keeps the
previous `E701` (continue from last round); see `check_esc_key` / sprint 0041.

## Stage-clear transition

Each round is one long stage. When the scroll engine reaches the end of a round's
stream it:

1. Writes the **next** round's stream-start pointer into `E722`.
2. Sets `E102` bit 5 (`level_complete`).

The main loop (`main_game_loop` / `LAB_4074`) sees bit 5 and jumps to
`level_complete_handler` (0x40DA), which:

1. Fades entities, then if `E722 != 0` calls **`resolve_round_from_ptr`** (0x9444)
   to convert `E722` back into a round number and writes it to `E701`.
2. Reloads the next round's tiles/stream, repaints the screen, picks the stage
   music (`E701 & 7`), then clears `E102` bit 5 and returns to the main loop.

So the round counter advances by *resolving the next stream pointer*, not by a
simple `INC`. `resolve_round_from_ptr` returns 1–8 for the eight round pointers
and **0** for anything below round 1 (the ending).

## End of game (after round 8)

When the final boss at the end of round 8 dies, the scroll engine (`LAB_92AF`)
sets:

- `E722 = 0xA6F4` (the **ending** stream pointer, below round 1), and
- `E102` bits **5 + 3** together (`level_complete` + `end_credits`).

Bit 5 is processed first: `level_complete_handler` runs, `resolve_round_from_ptr`
maps `0xA6F4 → 0` so **`E701 = 0`**, loads the ending background (the ZANAC-logo
path via `load_bg_level`), and clears bit 5. On the next frame the main loop sees
bit 3 and jumps to the **staff-credits** display (`LAB_46D5`). After the credits,
**ESC** (or timeout) returns to the title screen.

There is **no second loop**: beating round 8 leads to the ending/credits and then
title, not a harder lap.

## Live confirmation (sprint 0045)

Loading `savestates/game-end.oms` (captured at the round-8 boss kill):

- At load: `E102 = 0x28` (bits 5+3), `E701 = 8`, `E722 = 0xA6F4`.
- After ~4 s: `E701 → 0` (resolver mapped the ending pointer), `E102 = 0x08`
  (bit 5 cleared by `level_complete_handler`, bit 3 = credits still set, credits
  display running).

`resolve_round_from_ptr` round mapping confirmed for all 8 entries + the ending
pointer; the game-over path (`E102` bit 1 → `game_over_handler` sets bit 7 and
writes "GAME OVER") confirmed by injection. `tools/sprint0045_verify.py`.

## See also

- `input-state-machine.md` — full `E102` bit map and per-state key handling.
- `resolve_round_from_ptr.md` (0x9444), `stage_stream_ptr_table.md` (0x945C).
- `level_complete_handler.md` (0x40DA), `main_game_loop.md` (0x4042),
  `game_over_handler.md` (0x4663).
