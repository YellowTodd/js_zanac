---
letter: I
title: ALC — Adaptive Difficulty
coverage: done
status: done
---

# I — ALC (Adaptive Level Control)

## Role

Zanac's signature feature: difficulty that responds to how the player is doing.
The full mechanism is documented in the guide **[[alc-adaptive-difficulty]]**.

## Headline finding (sprint 0055)

**There is no "ALC level" byte.** Difficulty is encoded as the *rate at which the
spawn-schedule pointer advances*. The player's firing behaviour continuously
accelerates `spawn_pos` (E12E:E12F) and `level_seg_ctr` (E131); advancing them
faster makes the game reach the dense/fast part of the per-position spawn ramp
(0xBE76, consumed by [[update_spawn_table_ptr]]) sooner — so shooting more
*summons* harder waves. The old premise (a clamped level byte in 0xE100) was wrong.

## Two input families (refined sprint 0067)

The spawn accumulators (E12E/E12F/E131/E132) are driven by **two** sources, not
one:

1. **Player firing behaviour** — the *dynamic* input (sprint 0055, below). Fire
   cadence and fire/spawn-event counts advance the spawn pointer per shot / per
   base-frame.
2. **The per-round map-script** — the *scripted* input (sprint 0062). The
   row-triggered scroll interpreter ([[level_script_format]], `map_script_step`
   0x94C3) injects difficulty at chosen scroll rows:
   - **cmd 12 (`0x8C nn`)** — a signed **spawn-pace nudge** into the same
     accumulators: `E132 += nn` (saturating; also `E12E += nn` when negative),
     then `SET 0,(E12D)`. Byte-exact in [[ground_structure_placement]] /
     [[alc-adaptive-difficulty]]. So a round can bias difficulty up or down at
     specific positions regardless of how the player fires (e.g. round-6 preamble
     `8C 20` = +0x20).
   - **cmd 8 / cmd 9 (round banner / round-script jump)** — round transitions
     that **reset** the schedule: entering a round reloads the script and the
     per-round state, so the ALC ramp restarts each round.

   So the timeline the designer authored and the player's aggression **add
   together** into the same spawn schedule.

## How it works — family 1 (player firing)

| Variable | Addr | Role |
|----------|------|------|
| `alc_fire_cadence` | E13F | frames between shots; reset each shot; saturates 0xFF |
| `alc_shots_fired` | E140 | cumulative shots spawned |
| `alc_fire_events` | E141 | fire events (consumed by base path) |
| `spawn_event_ctr` | E142 | per-spawn counter (consumed by base path) |
| [[shot_rate_table]] | 0x7761 | cadence → spawn-advance amount (0x20…0x01) |

- **Per-shot feedback** ([[player_ship_update]] 0x7674): cadence → `shot_rate_table`
  → advance E12F + E131. Steady autofire → +1/shot; mashing → up to +0x20/shot;
  not firing → 0. **Confirmed live** (micro-exec, 7/7; `tools/alc_confirm.py`).
- **Base-encounter feedback** ([[handler_type35_projectile]] 0x8446, per frame):
  E12F += 0x10; level_seg += `shot_rate_table[E142+1]` + `(E141<8 ? 0x24-E141*4 : 1)`.
  *Fewer* shots during a base ⇒ bigger advance. (likely; read live.)
- **Shots-fired gate** (0x8374, [[handler_type61_large_descender]]): `E140 & 0x3F`
  vs `score_lo & 0x3F` times an entity transition.

## Resolved gaps

- ALC variable located: not one byte — the spawn pointers E12F/E131 (+ inputs above).
- Update routine: the player shot handler itself; no separate engine.
- Inputs sampled: fire cadence + fire/spawn event counts (per shot, per frame in base).
- How it indexes spawning: by advancing `spawn_pos` into [[update_spawn_table_ptr]]'s
  per-position ramp at 0xBE76.
- **`data_4b2a` (0x4B2A) is NOT ALC** — it is the [[structure_award_index_table]]
  (score-award indices by destruction sub-type; reader `add_score_for_subtype`
  0x4A6A, live-confirmed sprint 0065). Reclassified.
- **"Fire 2 raises ALC"** has no code hook (all ALC-var writers enumerated; none in
  fire-weapon code). Emergent at most.
- **The scripted input is real** (family 2): `map_script_step` cmd 12 writes the
  same accumulators — the map author, not just the player, shapes difficulty.

## Sprints

- **0055** — located and documented the engine (family 1). status: done.
- **0062** — decoded map-script cmd 12 byte-exactly (family 2, the scripted
  spawn-pace nudge). status: done.
- **0067** — reconciled the doc: ALC = two input families (player firing +
  map-script). status: done.
