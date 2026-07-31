---
address: 0x9393
kind: routine
name: gameplay_frame_loop
confidence: confirmed
inputs: { B: "number of frames to run" }
outputs: {}
clobbers: [AF, BC, DE, HL, IX, IY]
calls: [0x4306, 0x4DA5, 0x4AA5, 0x445F, 0x4649]
called_by: [0x46A8]
tags: [game-loop, entity, input, pause, vblank, timing]
sprint: "0032"
---

# gameplay_frame_loop

## Summary
Runs B frames of the active-gameplay loop: VBlank sync, STOP-key check, score
display update, entity dispatch, and player-hit processing.

## Analysis
Source lines 7134–7146.

```
gameplay_frame_loop(B):
  PUSH IX
LAB_9395:
  PUSH BC
  CALL 0x4306       ; wait_one_frame (VBlank sync, 60 fps)
  CALL 0x4DA5       ; pause_handler (STOP key → blocking blink loop)
  CALL 0x4AA5       ; score_display_update (flush dirty score to VRAM)
  CALL 0x445F       ; entity_dispatch (run all 26 entity handlers)
  CALL 0x4649       ; player_hit_handler (check E102 bit 0)
  POP BC
  DJNZ LAB_9395     ; repeat B times
  POP IX
  RET
```

Called by `wait_fire_or_timeout` (0x46A8) with B=1 to tick one frame while
waiting for a fire press during the game-over or credits screens.

The pause handler is called every frame so STOP-key pause works inside any
wait loop that routes through this routine.  Entity dispatch re-enables VDP
interrupts between slots (see `entity_dispatch` doc).
