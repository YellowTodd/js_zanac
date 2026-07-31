---
address: 0x4649
kind: routine
name: player_hit_handler
confidence: confirmed
inputs: {}
outputs: {}
clobbers: [AF, HL]
calls: [0x4C4D]
called_by: [0x9393]
tags: [player, lives, collision, e102]
sprint: "0032"
---

# player_hit_handler

## Summary
Processes the player-hit flag (E102 bit 0) each frame: decrements the lives
counter and either sets the respawn flag (bit 6) or the game-over flag (bit 1).

## Analysis
Source lines 851–865.

```
LD HL, 0xE102
BIT 0, (HL)       ; player_hit flag set?
RET Z             ; no — nothing to do
RES 0, (HL)       ; acknowledge flag
LD A, (0xE10A)    ; lives remaining
DEC A
LD (0xE10A), A
JR NZ, LAB_465d  ; lives > 0 → respawn
SET 1, (HL)       ; lives = 0 → E102 bit 1 = game_over
RET
LAB_465d:
SET 6, (HL)       ; E102 bit 6 = respawn
CALL 0x4C4D       ; update_status_bar (redraw lives/score HUD)
RET
```

`E10A` is the lives counter. Decremented here on each hit.  After going to
zero, `E102` bit 1 triggers `game_over_handler` (0x4663) on the next frame.
With lives remaining, bit 6 triggers a 64-frame respawn wait in the main loop
before reinitialising entity slot 0.
