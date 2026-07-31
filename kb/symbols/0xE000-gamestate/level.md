---
address: 0xE10B
kind: data
name: shot_level
confidence: confirmed
sprint: "0016"
tags: [game-state, player, shot]
---

# shot_level

## Summary

Shot upgrade level (0–5), shown near the "LEVEL" label on the HUD. Incremented
when the player collects a `power chip`; capped at 5 (`CP 0x06; JR C`). Each
level changes the shot's sprite pattern (SAT_NAME), Y-velocity, and maximum
simultaneous shots on screen. Reset to 0 on game start.

## Levels

| Level | Sprite | SAT_NAME | vy_raw | ~vy (stored) | Max simultaneous |
|-------|--------|----------|--------|--------------|-----------------|
| 0 | shot_single (pat10) | 0x28 | 0x04 | 0xFB | 2 |
| 1 | shot_single (pat10) | 0x28 | 0x06 | 0xF9 | 3 |
| 2 | shot_double (pat11) | 0x2C | 0x08 | 0xF7 | 2 |
| 3 | shot_double (pat11) | 0x2C | 0x09 | 0xF6 | 3 |
| 4 | shot_triple (pat12) | 0x30 | 0x0A | 0xF5 | 2 |
| 5 | shot_triple (pat12) | 0x30 | 0x0E | 0xF1 | 3 |

Level pairs (0/1, 2/3, 4/5) share the same sprite; the odd level has higher
velocity and one extra simultaneous shot.

## Param reload routine

When `shot_level` is incremented, `update_shot_params` (~0x7771) reloads
0xE10D (max_simultaneous), 0xE10E (vy_raw), and 0xE10F (sat_name) from the
6-entry table at 0x778F (3 bytes per entry: vy_raw, max_simultaneous, sat_name).
