---
name: alc-adaptive-difficulty
description: "Zanac's ALC (adaptive difficulty): there is no level byte — the player's firing cadence and fire-event density continuously accelerate the spawn-schedule pointer (E12F/E131), reaching harder spawn segments sooner. Primary feedback in player_ship_update (0x7674), base feedback in handler_type35 (0x8446)."
kind: guide
confidence: confirmed
sprint: "0055"
tags: [alc, difficulty, spawn, e13f, e131, e12f, shot-rate-table, adaptive]
---

# ALC — Adaptive Level Control

Zanac's signature feature. **It is not a difficulty *level*.** There is no clamped
"ALC byte"; difficulty is encoded as the **rate at which the spawn schedule is
advanced**. Aggressive/erratic firing pushes the spawn-position pointer forward
faster, so the game arrives at denser, faster-spawning level segments sooner — the
player effectively *summons* harder waves by shooting more.

**Two input families feed the same schedule** (refined sprint 0067):

1. **Player firing behaviour** — the dynamic input (this guide's main body): fire
   cadence (E13F) and fire/spawn-event counts advance the spawn pointer per shot
   and per base-frame.
2. **The per-round map-script** — the scripted input: the row-triggered scroll
   interpreter ([[level_script_format]]) nudges the same accumulators with
   **cmd 12** and resets them at **cmd 8 / cmd 9** round transitions (see
   "Second input" below).

Both write the same E12E/E12F/E131/E132 accumulators, so the authored timeline
and the player's aggression add together.

## The schedule it drives

Enemy spawning is paced by three coupled state bytes in [[game_state_block]]:

- `spawn_pos` (E12E:E12F) — 16-bit distance-into-stage accumulator.
- `level_seg_ctr` (E131) — segment counter; its carries bump the encounter chain.
- `spawn_table_ptr` (E133) — ROM pointer into the per-stage entity sequence.

[[update_spawn_table_ptr]] (0xBE27) reads `spawn_pos` (E12E), clamps it, and uses
it to index the per-segment tables at 0xBE7C (subtable max → E136) and the
**per-position spawn-rate ramp at 0xBE76** (`38 32 2C 22 1C 14 00` — reload values
that shrink, i.e. spawns get *faster* deeper into the stage). So **advancing
`spawn_pos` faster = reaching the fast/dense part of the ramp sooner.** That is the
entire payoff of ALC.

Carry out of E12F/E131 propagates via [[inc_encounter_inner]] (0xBFAB, E12E++) and
`SUB_bfc8` (0xBFC8, E130++) — the encounter counters.

## Second input family: the per-round map-script (family 2)

Besides the dynamic firing-cadence path (family 1, below), each round's
row-triggered map script ([[level_script_format]], `map_script_step` 0x94C3)
shapes the same schedule at authored scroll positions:

- **cmd 12 (`0x8C nn`)** — a **scripted spawn-pace nudge** (handler 0x977D;
  byte-exact in [[ground_structure_placement]]). The single **signed** operand
  `nn` adds to the same accumulators: `E132 += nn` (saturating; also `E12E += nn`
  when negative) then `SET 0,(E12D)`. So the ROM can bias difficulty up/down at
  chosen scroll positions independent of how the player fires (e.g. round-6
  preamble `0xAAF3: 8C 20` = `+0x20`). Every mainline script carries several.
- **cmd 8 / cmd 9 (round banner / round-script jump)** — round transitions that
  **reset** the schedule: a cmd-9 jump reloads the script from the next round's
  pointer (via `resolve_round_from_ptr`), restarting the per-round ramp, and the
  cmd-8 banner marks the boundary. So the ALC ramp is *per round*, not
  monotonic across the whole game.

This is the "scripted" half of ALC: the designer's authored timeline and the
player's aggression both write E12E/E12F/E131/E132 and add together. Confirmed
via sprint 0062's byte-exact grammar (all 9 scripts walk desync-free, cmd-12
operands pinned).

## Input variables

| Addr | Name | Role |
|------|------|------|
| E13F | `alc_fire_cadence` | frames since last shot fired; ++ every frame, reset to 0 each shot; saturates 0xFF |
| E140 | `alc_shots_fired` | cumulative shots actually spawned; ++ per shot |
| E141 | `alc_fire_events` | fire-cadence events (shots), ++ per shot; consumed/reset by the base path |
| E142 | `spawn_event_ctr` | per-entity-spawn counter; consumed/reset by the base path |

## Feedback path 1 — per shot (primary), in [[player_ship_update]] 0x7674

Runs every frame as part of the player handler. While the **shot** button is held
(E100 bit 4 active-low) it autofires on a fixed 20-frame period (E110 reload 0x14).
On each shot fired:

```
adv = (E13F >= 0x12) ? 1 : shot_rate_table[E13F - 2]   ; 0x7691 / 0x7761
E12F += adv ; if carry: inc_encounter (0xBFAB)          ; 0x76a7
E131 += adv ; if carry: SUB_bfc8     (0xBFC8)           ; 0x76b0
E13F  = 0                                                ; 0x76b9
E141++ (saturating)                                      ; 0x76bf
... spawn the shot entity into the E320 slot table ...
E140++                                                   ; 0x76e8
```

`E13F` is the **cadence** = frames between consecutive shots. [[shot_rate_table]]
maps it inversely:

| cadence E13F | 0x02 | 0x03 | 0x04 | 0x08 | 0x11 | ≥0x12 |
|---|---|---|---|---|---|---|
| advance | 0x20 | 0x10 | 0x0A | 0x04 | 0x02 | 0x01 |

- **Steady autofire** (hold the button): cadence ≈ 20 frames ⇒ advance **1** per
  shot — the schedule creeps forward at the baseline rate.
- **Mashing / erratic tapping**: each tap re-primes E110 to 1, so the next held
  frame fires immediately with a tiny cadence ⇒ advance up to **0x20** per shot —
  the schedule lurches forward and many more enemies appear.
- **Not firing at all**: this path never runs ⇒ **zero** advance from firing.

(Confirmed live: micro-exec of the block reproduced the table exactly, 7/7; IDLE
gives zero advance, firing raises on-screen enemy count — `tools/alc_confirm.py`.)

## Feedback path 2 — per frame during a base, in [[handler_type35_projectile]] 0x8446

While a base "eye" is active it advances the schedule every frame and folds in the
player's fire activity (likely; read live, not micro-exec'd):

```
E12F += 0x10 ; if carry: inc_encounter                  ; 0x844d
adv1 = (E142 >= 0x11) ? 1 : shot_rate_table[E142+1]     ; 0x8457
E131 += adv1 ; carry -> SUB_bfc8
adv2 = (E141 < 8) ? (0x24 - E141*4) : 1                 ; 0x8473
E131 += adv2 ; carry -> SUB_bfc8
E142 = 0 ; E141 = 0                                      ; 0x848d/0x8490
```

Note the **inverse** coupling of `adv2`: the *fewer* shots the player fired during
the base window (small E141), the *bigger* the advance — so passive play during a
base still ramps pressure. The base eye therefore self-paces its own bullet/spawn
density off the player's aggression.

## Minor use — shots-fired as a timing gate (0x8374)

[[handler_type61_large_descender]] compares `E140 & 0x3F` to `score_lo & 0x3F`; on
coincidence it transitions the entity (type → 0x3E). A lightweight reuse of the
shot counter as a pseudo-random clock, not a difficulty knob in itself.

## What ALC is **not**

- **No level byte / no clamp.** Searched the whole 0xE100 block; the difficulty
  state is the spawn pointers themselves.
- **`shot_rate_table` is not autofire spacing.** Spacing is the fixed 20-frame
  E110 period; the table is the spawn-advance amount.
- **`data_4b2a` (0x4B2A) is not ALC.** It has no static reader and lives in the HUD
  digit-draw area (before `write_digit_to_vram` 0x4B83).
- **"Taking Fire 2 raises ALC"** ([[game-description]]) has no scripted hook in this
  MSX build: no fire-weapon code writes any ALC variable. Any such effect is
  emergent (e.g. the Field Shutter changing how the player fires).

## Related

[[G-enemy-and-spawn-system]] (consumer), [[update_spawn_table_ptr]],
[[shot_rate_table]], [[player_ship_update]], [[game_state_block]],
[[round-progression]] (round selects the per-stage spawn data the ramp walks).
