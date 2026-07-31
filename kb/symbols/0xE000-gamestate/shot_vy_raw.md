---
address: 0xE10E
kind: data
name: shot_vy_raw
confidence: confirmed
sprint: "0016"
tags: [game-state, player, shot]
---

# shot_vy_raw

## Summary

Raw Y-velocity parameter for the player shot, loaded from shot param table
at 0x778F (byte offset 0). The type-2 handler stores `CPL(shot_vy_raw)` into
IX+0x09 (Y velocity integer), making the shot move upward. Values: 0x04/0x06/
0x08/0x09/0x0A/0x0E for shot levels 0–5.
