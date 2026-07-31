---
address: 0x48A9
end: 0x48B7
kind: routine
name: sprite_shadow_push
confidence: confirmed
inputs:
  IX: entity slot pointer (0xE300 + n*32)
  C: behaviour-flags byte (= IX+0x0C), loaded by the caller
outputs:
  E122: advanced by 4 (via the SAT-write tail)
clobbers: [AF, BC, DE, HL]
calls: [0x48DE, 0x48F8, 0x4912, 0x48B8]
called_by: []
tags: [sprite, vblank, entity, motion]
sprint: "0043"
---

# sprite_shadow_push

## Summary

Linear-motion + animation dispatcher, entered by **fall-through** from
`entity_update` (0x4898) with `C = IX+0x0C` (behaviour flags). It applies the
flagged per-axis motion and animation, then falls into `sprite_sat_write`
(0x48B8) to queue the entity's SAT shadow entry.

> Correction (sprint 0035): the previous entry at this address actually decoded
> the SAT-write tail at 0x48B8 — that content now lives in `sprite_sat_write.md`.
> 0x48A9 itself is the motion dispatch shown below. There are **no direct callers**
> of 0x48A9; it is only reached via the 0x4898 fall-through.

## Analysis

```
48A9  BIT 0,C            ; apply Y velocity?
48AB  CALL NZ,0x48DE     ;   → Y_motion_sub  (IX+1:6 += IX+8:9, despawn if Y≥0xD0)
48AE  BIT 1,C            ; apply X velocity?
48B0  CALL NZ,0x48F8     ;   → X_motion_sub
48B3  BIT 2,C            ; advance animation?
48B5  CALL NZ,0x4912     ;   → anim_sub
                         ; ── falls into sprite_sat_write (0x48B8) ──
```

`C` is the behaviour-flags byte documented in `entity_update.md`: bits 0–2
(motion X/Y, animation) are consumed here; bits 3–4 (homing) were handled by
`entity_update` before the fall-through.

## Live confirmation (sprint 0043)
A non-breaking breakpoint at 0x48A9 counted **85 executions in 0.5 s** of active
gameplay (≈ several entities × 59 Hz), confirming the address is reached on the
hot per-frame entity path via the `entity_update` (0x4898) fall-through. The
resulting sprites move/animate on screen and the SAT shadow it feeds matches
VRAM (see `sat_dma_to_vram`). `tools/sprint0043_verify.py`.

## See also

- `entity_update.md` — 0x4898, the homing wrapper that falls in here.
- `sprite_sat_write.md` — 0x48B8, the SAT-shadow append this falls into.
- `sat_dma_to_vram.md` — ISR segment that DMAs the 0xE000 shadow to VRAM.
- `entity_clear.md` — 0x48D0, despawn target of Y_motion_sub.
