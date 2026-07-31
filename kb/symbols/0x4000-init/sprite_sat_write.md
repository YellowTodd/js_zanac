---
address: 0x48B8
end: 0x48CF
kind: routine
name: sprite_sat_write
confidence: confirmed
inputs:
  IX: entity slot pointer (0xE300 + n*32)
outputs:
  E122: advanced by 4 (next free shadow slot)
clobbers: [AF, BC, DE, HL]
calls: []
called_by: [0x48B5, 0x73C5, 0x83F2, 0x8443]
tags: [sprite, vblank, entity, sat]
sprint: "0043"
---

# sprite_sat_write

## Summary

Appends one 4-byte SAT (Sprite Attribute Table) entry to the sprite-shadow
buffer at 0xE000, using the walk pointer at `0xE122`, then advances the pointer
by 4. Reached two ways:

1. **Fall-through** from `sprite_shadow_push` (0x48A9) after linear motion +
   animation have been applied (the normal path via `entity_update`).
2. **Direct `JP 0x48B8`** from handlers that compute their own sprite fields and
   want to emit the SAT entry without running the standard motion subs
   (0x73C5, 0x83F2, 0x8443).

This is the routine the previous `sprite_shadow_push.md` (sprint 0006) actually
decoded — it has been split out here so 0x48A9 can document the motion dispatch
separately.

## Analysis

```
48B8  LD HL,(0xE122)    ; shadow walk pointer (starts at 0xE000)
48BB  PUSH IX; POP DE   ; DE = IX = entity slot base
48BE  INC DE            ; DE → slot[1]
48BF  LD A,(DE)         ; A = slot[1] = Y position (bottom edge, 1-indexed)
48C0  SUB 0x11          ; convert to SAT Y byte (− 17)
48C2  LD (HL),A         ; shadow[0] = SAT Y
48C3  EX DE,HL          ; DE = shadow ptr, HL = slot+1
48C4  INC HL            ; HL → slot[2]
48C5  INC DE            ; DE → shadow+1
48C6  LD BC,3; LDIR     ; shadow[1..3] ← slot[2..4]  (X, name, colour/EC)
48CB  LD (0xE122),DE    ; advance walk pointer by 4
48CF  RET
```

## SAT encoding

- `shadow[0]` = SAT Y = `slot[1] − 17` (slot[1] holds bottom-edge row, 1-indexed).
- `shadow[1]` = SAT X = `slot[2]` (pixel column, direct).
- `shadow[2]` = SAT name = `slot[3]`; in 16×16 mode pattern index = `slot[3] >> 2`.
- `shadow[3]` = SAT colour / early-clock byte = `slot[4]`.

The ISR later DMAs this shadow buffer to VRAM. `0xE122` is reset to 0xE000 at
the top of each frame so entries accumulate in dispatch order.

## Live confirmation (sprint 0043)
Micro-exec with a fake slot at 0xE780 = `[00 64 50 38 0F]` and `(0xE122)=0xE01C`:
after calling 0x48B8 the shadow entry was `[53 50 38 0F]` (Y = 0x64−0x11 = 0x53;
X/name/colour copied verbatim) and `(0xE122)` advanced to 0xE020 (+4). Matches
the SAT encoding exactly. `tools/sprint0043_verify.py`.

## See also

- `sprite_shadow_push.md` — 0x48A9, the motion-dispatch wrapper that falls in here.
- `entity_update.md` — 0x4898, the homing wrapper above that.
