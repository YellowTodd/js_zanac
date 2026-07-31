---
address: 0x4d65
end: 0x4da4
kind: data
name: vel_dir_table
confidence: confirmed
sprint: "0048"
tags: [velocity, vector, direction, entity, weapon]
---

# vel_dir_table

## Summary

16-entry **unit-velocity vector table** read by [[set_velocity_from_dir]]
(0x4cf7). Each entry is 4 bytes = two signed 16-bit words: **X-component** then
**Y-component**, at magnitude ≈128 (0x80). Direction index 0 points "down"
(+Y); the table walks clockwise in 16 steps (22.5° each).

## Layout (dir: X, Y)

| dir | X | Y | | dir | X | Y |
|-----|------|------|-|-----|------|------|
| 0 | 0 | +128 | | 8 | 0 | −128 |
| 1 | +48 | +118 | | 9 | −48 | −118 |
| 2 | +90 | +90 | | 10 | −90 | −90 |
| 3 | +118 | +48 | | 11 | −118 | −48 |
| 4 | +128 | 0 | | 12 | −128 | 0 |
| 5 | +118 | −48 | | 13 | −118 | +48 |
| 6 | +90 | −90 | | 14 | −90 | +90 |
| 7 | +48 | −118 | | 15 | −48 | +118 |

(+Y = down, +X = right, MSX screen coordinates.)

## Neighbours

- 0x4d42 `dir_angle_thresholds` (3 bytes: 0x32,0x6a,0xab) — octant cut-points
  used by the angle→direction code just before 0x4cf7.
- 0x4d45 `dir_remap_table` (32 bytes) — octant/quadrant remap into the 0-15 index.

## Confirmed (sprint 0048)

`set_velocity_from_dir` output matched these vectors for all tested directions.
`tools/sprint0048_verify.py`.
