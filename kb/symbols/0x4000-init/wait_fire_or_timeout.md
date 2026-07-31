---
address: 0x46A8
kind: routine
name: wait_fire_or_timeout
confidence: confirmed
inputs: { BC: "iteration count (frames to wait)" }
outputs: { carry: "set if fire was detected, clear if timeout" }
clobbers: [AF, BC, DE, HL, IX]
calls: [0x9480, 0x9393, 0x46BC]
called_by: [0x4663, 0x46D9]
tags: [timing, input, fire, credits, game-over]
sprint: "0032"
---

# wait_fire_or_timeout

## Summary
Runs the game loop for up to BC frames.  Returns early with carry set if the
player presses a fire key (SHIFT, SPACE, Z, or joystick trigger A).  Returns
without carry if BC reaches zero without a fire press.

## Analysis
Source lines 898–910.

```
wait_fire_or_timeout(BC):
  PUSH BC
  CALL 0x9480       ; scroll_velocity_ctrl (keep scroll running)
  LD B, 1
  CALL 0x9393       ; gameplay_frame_loop(B=1) — one frame
  CALL 0x46BC       ; fire_edge_detect → carry if rising-edge fire
  POP BC
  RET C             ; fire pressed — return with carry set
  DEC BC
  LD A, B
  OR C
  JR NZ, wait_fire_or_timeout   ; loop if BC != 0
  RET               ; timeout — return without carry
```

Used in two places:
- `game_over_handler` (0x4663): BC = 0x320 (800 frames ≈ 13 s).
- End-credits sequence (0x46D9): BC varies per credit entry.

The inner `gameplay_frame_loop` call with B=1 runs one VBlank-synced frame
including input, entity dispatch, and the pause handler, so STOP-key pause
still works during the wait.

`scroll_velocity_ctrl` is called once before the loop (not every frame) to
maintain the scroll momentum parameter; the scroll VRAM update itself happens
inside `gameplay_frame_loop` → `entity_dispatch`.
