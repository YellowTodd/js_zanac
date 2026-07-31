---
address: 0xE14B
kind: data
name: fire_type
confidence: likely
sprint: "0016"
tags: [game-state, fire, weapon]
---

# fire_type

## Summary

Current fire weapon type (0–7), shown near the "FIRE" label on the HUD. Starts
at 0 on game start. Upgraded (via `0x7548`) when the player collects a `power
chip` while `shot_level` (0xE10B) is already at maximum (5) — every 5 such
over-capped chips advance the fire type by one.

Read by the type-3 entity handler (fire weapon 0 projectile) at 0x7253 via
`CALL 0x5c2e` to determine projectile behavior (direction, spread).

## Known fire weapon effects

| Type | Description |
|------|-------------|
| 0 | large_circle projectile, all 16 colors, fires in ship movement direction |
| 1–7 | behavior not yet mapped (sprint 0017 candidate) |
