---
address: 0xE10D
kind: data
name: shot_max_simultaneous
confidence: confirmed
sprint: "0016"
tags: [game-state, player, shot]
---

# shot_max_simultaneous

## Summary

Maximum number of player shot entities that can be active simultaneously (2 or 3).
Loaded from the shot param table at 0x778F (byte offset 1 of each entry) when
`shot_level` (0xE10B) changes. The shot-spawn routine scans entity slots 1–N
where N = this value; if all are occupied the spawn is skipped.

Value 2 for shot levels 0, 2, 4 (base tiers); value 3 for levels 1, 3, 5 (fast tiers).
