---
address: 0x778f
end: 0x77a0
kind: data
name: shot_power_table
confidence: confirmed
sprint: "0048"
tags: [shot, weapon, power, table, player]
---

# shot_power_table

## Summary

6-entry table (3 bytes each, indexed by `shot_level` E10B & 0x0f) read by
[[load_shot_params]] (0x7771). Maps the normal-shot power level (raised by power
chips) to the shot's vertical speed, on-screen cap, and sprite pattern.

Byte 0 → **E10E** `shot_vy_raw` (vertical speed); byte 1 → **E10D**
`shot_max_simultaneous` (max shots on screen); byte 2 → **E10F** `shot_sat_name`
(sprite pattern name).

## Layout

| level | E10E vy | E10D cap | E10F name |
|-------|---------|----------|-----------|
| 0 | 0x04 | 2 | 0x28 |
| 1 | 0x06 | 3 | 0x28 |
| 2 | 0x08 | 2 | 0x2c |
| 3 | 0x09 | 3 | 0x2c |
| 4 | 0x0a | 2 | 0x30 |
| 5 | 0x0e | 3 | 0x30 |

Even levels cap at 2 shots, odd levels at 3; sprite name steps 0x28→0x2c→0x30
every two levels (the visible "thicker" shot upgrade). The table is 6 entries;
`shot_level` is capped at 5 by the chip-pickup logic, so indices 6-15 are never
used (they would read into the code at 0x77a1).

## Confirmed (sprint 0048)

`load_shot_params(E10B=lvl)` set E10E/E10D/E10F to `shot_power_table[lvl]` for
levels 0-5. `tools/sprint0048_verify.py`.

## One chip raises LEVEL but not the stream count (confirmed 2026-07-30)

Levels **0 and 1 share sprite 0x28** (one stream); 0x2C (two) starts at level
2 and 0x30 (three) at level 4. So a single power chip bumps LEVEL, the shot
speed (4 -> 6) and the in-flight cap (2 -> 3), but the shot still *looks* the
same - the second stream needs a second chip.

This was queried against the original during the web port and the ROM's
reading was confirmed correct by play-testing: the original also only advances
LEVEL on the first chip. Supporting evidence gathered at the time, worth
keeping because it pins the whole chain: the table base is the `LD HL,0x778F`
at 0x7771, the chip's award is a single `INC A` at 0x78DA,
`player_ship_handler` seeds `E10B = 0` at 0x7603, a type-6 box drops exactly
**one** chip (0x7882) and a type-68 box wave contains at most one type-6 box.
