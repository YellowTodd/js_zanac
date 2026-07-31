---
id: "0055"
status: done
range: 0x7674-0x76b9,0x8446-0x8490,0x8374
strategy: subsystem_slice
subsystems: [I]
---

# Sprint 0055 — Subsystem I (ALC / adaptive difficulty): locate & document the engine

## Goal

Find the ALC ("Automatic Level of Difficulty Control") engine: the RAM variable(s),
the update routine, the inputs it samples, and how it feeds enemy spawning. The
subsystem was a 5% stub — premise was that an "ALC level byte" lived somewhere in
the 0xE100 block and had not been located.

## Method

1. Differential RAM sweep (`tools/alc_explore.py`): time-series of 0xE100..0xE1FF
   under IDLE vs continuous-fire. Flagged bytes that climb under fire only.
2. Write-watchpoint writer hunt (`tools/alc_writers.py`) on the candidates.
3. Static decode of the writer code; cross-trace the consumers.
4. Deterministic micro-exec confirmation of the table mapping (`tools/alc_confirm.py`).

## Summary

**Subsystem I → fully documented ✓.** Full mechanism in
[[alc-adaptive-difficulty]].

### Headline finding

**There is no "ALC level" byte.** Difficulty is encoded as the *rate at which the
spawn-schedule pointer is advanced*. The player's firing behaviour continuously
accelerates the spawn position (`spawn_pos` E12E:E12F) and the segment counter
(`level_seg_ctr` E131); advancing them faster makes the game reach denser/faster
spawn segments sooner (see [[update_spawn_table_ptr]] / 0xBE76 ramp). The previous
premise (a clamped level byte in 0xE100) was wrong.

### Confirmed (live micro-exec, `tools/alc_confirm.py`, 7/7)

Primary ALC path inside [[player_ship_update]] (0x7691–0x76b9): drove the block
with controlled `E13F` (fire cadence) and read the advance applied to E12F/E131.

| E13F (cadence) | advance | note |
|---|---|---|
| 0x02 | 0x20 | mashing / erratic fire → huge jump |
| 0x03 | 0x10 | |
| 0x04 | 0x0A | |
| 0x08 | 0x04 | |
| 0x11 | 0x02 | |
| ≥0x12 | 0x01 | steady autofire (period 20) → minimal |

Advance is applied to **both** E12F and E131; E13F resets to 0 each shot. Matches
[[shot_rate_table]] exactly.

### Confirmed (live diff, `tools/alc_explore.py` / `alc_confirm.py`)

- IDLE (no fire) → **zero** schedule advance, 0 shots.
- Firing → E131/E12F climb, peak on-screen enemies rises (8 → 10).
- Writers of E13F/E140/E141 are all in the shot handler (PC 0x7677/0x76b9/0x76bc/0x76e8).

### Mechanics (static, cross-traced)

- **Inputs**: fire cadence (E13F), cumulative shots (E140), fire-event count (E141),
  spawn-event count (E142).
- **Primary feedback** (per shot, 0x7674): cadence → `shot_rate_table` → advance
  E12F + E131. Carry bumps the encounter counters ([[inc_encounter_inner]] 0xBFAB,
  `SUB_bfc8` 0xBFC8).
- **Base-encounter feedback** (per frame, [[handler_type35_projectile]] 0x8446):
  E12F += 0x10; `level_seg` += `shot_rate_table[E142+1]`; `level_seg` += `(E141<8 ?
  0x24-E141*4 : 1)` → *fewer* fire events during a base ⇒ *bigger* advance. Resets
  E141=E142=0. (likely — read live but not micro-exec'd.)
- **Shots-fired gate** (0x8374, [[handler_type61_large_descender]]): `E140 & 0x3F`
  compared to `score_lo & 0x3F` to time an entity transition — a minor ALC-flavoured
  use of the shot counter as entropy.

### Corrections

- **`shot_rate_table` (0x7761) is NOT auto-fire spacing.** Shot spacing is fixed at
  20 frames (E110 reload 0x14). The table is the ALC spawn-advance amount. Renamed
  role; `tags` updated. (Name kept to preserve links.)
- **E13F is the fire *cadence* counter, not "auto-fire spacing".** Updated
  [[game_state_block]] and [[player_ship_update]].
- **E140 / E141 removed from `game_state_block` "stable unknown 0x00" list** — they
  are ALC counters (were 0x00 only because the IDLE sample never fired).
- **0x4B2A (`data_4b2a`) is NOT ALC.** CLAUDE.md flagged it "likely ALC/difficulty
  params"; it has no static reader, sits in the HUD digit-draw area (just before
  `write_digit_to_vram` 0x4B83), and writes nothing in the spawn path. Reclassified
  as HUD-area unknown.
- **"Taking Fire 2 raises ALC" (game-description folklore) has no code hook.** All
  writers of the ALC vars were enumerated; none live in fire-weapon code. Any such
  effect on the MSX build is emergent, not a scripted bump.

### Tools

`tools/alc_explore.py`, `tools/alc_writers.py`, `tools/alc_confirm.py`.
