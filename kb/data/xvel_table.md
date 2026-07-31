---
address: 0x7758
end: 0x7760
kind: data
name: xvel_table
confidence: confirmed
sprint: "0048"
tags: [player, ship, movement, velocity, table]
---

# xvel_table

## Summary

9-byte table indexed by **E10C** (`player_x_vel` selector, 0-8) read by
[[player_ship_update]] (0x7612). The selector is computed in
[[read_player_input]] from the 4 direction bits (start 4 = centre; right +1,
left −1, up −3, down +3). Its value picks a **direction index** that is then fed
to [[set_velocity_from_dir]] (`CALL 0x4cf7` with E = table value) to set the
ship's velocity vector.

## Layout

| E10C | value | note |
|------|-------|------|
| 0 | 0x06 | |
| 1 | 0x08 | |
| 2 | 0x0a | |
| 3 | 0x04 | |
| 4 | 0x0c | centre — **skipped** (0x7618 `CP 4; JP Z`), never read |
| 5 | 0x0c | |
| 6 | 0x02 | |
| 7 | 0x00 | |
| 8 | 0x0e | |

## Confirmed (sprint 0048)

Steering live moved the ship in the expected axis (right → E302 up, left → down,
up → E301 down), exercising this table → `set_velocity_from_dir`.
`tools/sprint0048_live.py`.
