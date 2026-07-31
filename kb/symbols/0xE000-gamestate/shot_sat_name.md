---
address: 0xE10F
kind: data
name: shot_sat_name
confidence: confirmed
sprint: "0016"
tags: [game-state, player, shot]
---

# shot_sat_name

## Summary

SAT_NAME byte (sprite pattern selector) for the player shot, loaded from shot
param table at 0x778F (byte offset 2). Stored directly into IX+0x03 by the
type-2 handler init. Values: 0x28 (shot_single, pat10) for levels 0–1; 0x2C
(shot_double, pat11) for levels 2–3; 0x30 (shot_triple, pat12) for levels 4–5.
