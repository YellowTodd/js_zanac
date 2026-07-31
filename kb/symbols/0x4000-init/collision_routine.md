---
address: 0x4560
end: 0x45C8
kind: routine
name: collision_routine
confidence: confirmed
sprint: "0030"
calls: []
called_by: [0x44D4]
tags: [collision, entity, sprite]
---

# collision_routine

## Summary

Two tightly-coupled routines that together implement software sprite collision
detection. `hitbox_setup_ix` (0x45A0) computes IX's hitbox bounds into
registers; `hitbox_check_iy` (0x4560) checks IY's sprite against those bounds.
Both index the same size table at 0x45C9.

Called from `entity_post` flow (via 0x44D4) with IX = current entity,
IY = player-side entity (player shot, fire weapon, or player ship).
Returns carry set if overlap (collision detected).

## hitbox_setup_ix — 0x45A0–0x45C8

Computes IX entity's hitbox boundaries from its sprite fields and stores them
in caller-saved registers for use by `hitbox_check_iy`.

**Inputs:** IX = entity slot pointer  
**Outputs:**
- BC = (B: Y bottom edge, C: Y top edge) — IX's vertical hitbox bounds
- BC' (shadow) = (B': X right edge, C': X left edge) — IX's horizontal hitbox bounds

```
45A0  LD A,(IX+3)    ; A = IX.sat_name
45A3  SRL A          ; A = sat_name >> 1  (size-table index)
45A5  LD E,A
45A6  LD D,0
45A8  LD HL,0x45C9   ; size table base
45AB  ADD HL,DE      ; HL → size_table[sat_name >> 1]
45AC  LD A,(IX+1)    ; A = IX.y
45AF  LD D,A         ; D = y
45B0  LD E,(HL)      ; E = Y hitbox half-size (table byte 0)
45B1  ADD A,E        ; A = y + half-size  (bottom edge)
45B2  LD B,A         ; B = Y bottom
45B3  LD A,D
45B4  ADD A,0x10     ; A = y + 16
45B6  SUB E          ; A = y + 16 - half-size  (top edge)
45B7  INC HL         ; HL → size_table[idx + 1]
45B8  LD C,A         ; C = Y top
45B9  PUSH BC        ; save Y bounds
45BA  LD A,(IX+2)    ; A = IX.x
45BD  LD D,A
45BE  LD E,(HL)      ; E = X hitbox half-size (table byte 1)
45BF  ADD A,E        ; A = x + half-size  (right edge)
45C0  LD B,A         ; B' = X right
45C1  LD A,D
45C2  ADD A,0x10     ; A = x + 16
45C4  SUB E          ; A = x + 16 - half-size  (left edge)
45C5  LD C,A         ; C' = X left
45C6  EXX            ; shadow BC ← X bounds
45C7  POP BC         ; BC ← Y bounds
45C8  RET
```

## hitbox_check_iy — 0x4560–0x459F

Checks IY entity's sprite against IX's pre-computed hitbox bounds (BC / BC').
Returns carry set if the sprites overlap on both axes (collision).

**Inputs:**
- IY = entity slot to test (player shot, fire weapon, player)
- BC = IX's Y bounds (B: bottom, C: top), BC' = IX's X bounds (B': right, C': left)

**Outputs:** carry set = overlap (collision), carry clear = no overlap  
**Clobbers:** A, D, E, HL, BC, BC'

```
4560  OR A           ; clear carry (default: no collision)
4561  LD A,(IY+3)    ; A = IY.sat_name
4564  SRL A          ; A = sat_name >> 1
4566  LD E,A
4567  LD D,0
4569  LD HL,0x45C9   ; size table
456C  ADD HL,DE
456D  LD A,(IY+1)    ; A = IY.y
4570  CP 0xF0        ; y >= 0xF0? (off-screen)
4572  RET NC         ; no collision if off-screen
4573  LD D,A
4574  LD E,(HL)      ; E = IY's Y half-size
4575  ADD A,E        ; A = IY y_bottom
4576  CP B           ; vs IX Y_bottom (B)
4577  JP NC,0x4583
457A  LD A,D
457B  ADD A,0x10
457D  SUB E          ; A = IY y_top
457E  CP B           ; compare with IX Y_bottom
457F  CCF
4580  RET NC         ; no Y overlap → return carry clear
4581  JR 0x4585      ; Y overlap confirmed; check X
4583  CP C           ; vs IX Y_top (C)
4584  RET NC         ; no Y overlap
4585  INC HL
4586  LD A,(HL)      ; A = IY's X half-size
4587  EXX            ; restore shadow BC (IX X bounds)
4588  LD E,A
4589  LD A,(IY+2)    ; A = IY.x
458C  CP 0xF0        ; off-screen check
458E  RET NC
458F  LD D,A
4590  ADD A,E        ; A = IY x_right
4591  CP B           ; vs IX X_right (B')
4592  JP NC,0x459D
4595  LD A,D
4596  ADD A,0x10
4598  SUB E          ; A = IY x_left
4599  CP B           ; compare with IX X_right
459A  CCF
459B  EXX
459C  RET            ; carry clear = no X overlap
459D  CP C           ; vs IX X_left (C')
459E  EXX
459F  RET            ; carry = (IY x_left < IX X_right), i.e. overlap
```

## Notes

- The `OR A` at 0x4560 clears carry before the check (safe default).
- Off-screen test (`CP 0xF0`) applies to both Y and X; an entity at ≥ 240 on
  either axis is treated as out-of-play and cannot collide.
- Size table at 0x45C9 encodes pairs of bytes per sprite: see
  `collision_size_table.md`. The Y half-size is at `table[sat_name >> 1]`; the
  X half-size is at `table[(sat_name >> 1) + 1]`.
- The routine never references 0x716B. The sprint 0021 partial decode
  incorrectly identified a `LD HL,0x716B` here; the actual ROM byte sequence
  is `LD HL,0x45C9`.

## Calling convention (entity_post flow)

```
entity_post → CALL 0x45A0   ; compute IX hitbox → BC / BC'
           → CALL 0x44D4   ; sets IY, calls CALL 0x4560; RET C if collision
           → JP C, 0x453E  ; collision path
```

Live verification (sprint 0030): 0x453E BP fired with IX=0xE420 (type 44,
ground struct) and IY=0xE340 (type 2, player shot). Confirms player shots
are checked against ground structures each frame.
