---
address: 0xBF2C
end: 0xBF93
kind: routine
name: ground_struct_spawn_ctrl
confidence: confirmed
inputs:  {}
outputs: {}
clobbers: [AF, AF', BC, DE, HL, IX]
calls:   [0xBE27, 0x4496, 0xBF94, 0xBFA0]
called_by: [0x4082]
tags: [scroll, entity, spawn, ground-structure]
sprint: "0011"
---

# ground_struct_spawn_ctrl

## Summary

> **Two corrections (2026-07-30, found while porting).**
>
> 1. **The 0xE125 immediate trigger spawns entity type 68, not 44.** The write
>    at 0xBFA8 is `LD (HL),0x44` — hex 0x44 = **68 decimal**, the
>    invisible score-based bonus entity (handler 0x77A1), not the type-44
>    (0x2C) ground structure this file calls it. The trigger is raised by the
>    every-16th-kill counter in the type-35 death handler (0x84BC:
>    0xE124 countdown, reload 0x10), which fits a kill-streak bonus, not
>    terrain. Prose below saying "type-44 NOW" should be read as "byte 0x44".
> 2. **Who activates the stream:** 0xE12D bit 1 is set by exactly one writer —
>    `title_screen_init`'s `LD (IX+0x2D),0x3` at 0x4225 (with bit 0 requesting
>    the first table recompute). Map-script cmd 0 can overwrite the whole byte,
>    but round 1's script contains no cmd 0, so without the 0x4225 seed the
>    airborne stream never starts. The same block seeds 0xE124 = 6 (0x41F9),
>    the first immediate-bonus countdown.

Main-loop routine called every frame from 0x4082. Sets its own `IX = 0xE100`
(the game-state block). Reads the level entity spawn table (pointed to by
0xE133–0xE134) and spawns the next entity type into a free slot when the
per-frame spawn timer fires. Also handles the immediate type-44 ground-structure
trigger flag at 0xE125 bit 0.

This is **not** called via `entity_dispatch`; it is part of the main scroll/spawn
engine alongside `scroll_velocity_ctrl` and `scroll_map_reader`.

## Analysis

```
BF2C  LD IX, 0xE100         ; always uses game-state block, ignores caller's IX
BF30  BIT 3,(IX+0x02)       ; check E102 bit3 — global spawn-block flag
BF34  RET NZ                ; blocked → skip
BF35  BIT 0,(IX+0x2D)       ; check E12D bit0 — "call BE27" flag
BF39  CALL NZ, 0xBE27       ; if set: run scroll-position update (clears bit0)
BF3C  BIT 0,(IX+0x25)       ; check E125 bit0 — "spawn type-44 NOW" trigger
BF40  JR NZ, 0xBFA0         ; if set → immediately allocate slot, write type 0x44
BF42  BIT 3,(IX+0x2D)       ; check E12D bit3 — stream-block flag
BF46  RET NZ
BF47  LD HL, 0xE138
BF4A  BIT 1,(IX+0x2D)       ; check E12D bit1 — "active spawn stream" flag
BF4E  RET Z                 ; no stream → nothing to spawn
BF4F  LD A, (HL)            ; A = E138 (timer reload value)
BF50  DEC HL                ; HL = E137
BF51  DEC (HL)              ; decrement E137 (spawn timer)
BF52  RET NZ                ; not fired → done
BF53  LD (HL), A            ; reload timer from E138
BF54  DEC HL                ; HL = E136
BF55  LD A, (IX+0x26)       ; stream_slot_ctr
BF58  INC (IX+0x26)         ; advance counter
BF5B  AND 0x0F              ; mod 16
BF5D  JP Z, 0xBF94          ; every 16th slot → spawn type 0x3D (61) instead
BF60  LD A, (HL)            ; else: read from E136
BF61  DEC HL                ; HL = E135
BF62  LD C, (HL)            ; C = E135
BF63  INC (HL)              ; E135++
BF64  DEC A
BF65  CP C
BF66  JR NZ, 0xBF6A
BF68  LD (HL), 0x00         ; reset E135 when A==C
BF6A  LD B, 0
BF6C  LD HL, (0xE133)       ; HL = spawn table pointer
BF6F  ADD HL, BC            ; index by counter
BF70  LD A, (HL)            ; A = entity type to spawn
BF71  AND A
BF72  RET Z                 ; type 0 = end of table
BF73  EX AF, AF'            ; save type
BF74  CALL 0x4496           ; allocate free entity slot → HL
BF77  RET C                 ; no free slot
BF78  EX AF, AF'            ; restore type
BF79  LD (HL), A            ; write entity type into new slot!
BF7A  LD A, (IX+0x2F)
BF7D  ADD A, 0x08
BF7F  LD (IX+0x2F), A       ; E12F += 8 (spawn-position lo accumulator)
BF82  JR NC, 0xBF8C
BF84  INC (IX+0x2E)         ; carry → E12E++ (hi byte)
BF87  JR NZ, 0xBF8C
BF89  DEC (IX+0x2E)         ; saturate: keep E12E non-zero at 0xFF
BF8C  INC (IX+0x42)         ; E142++ (spawn event counter)
BF8F  RET NZ
BF90  DEC (IX+0x42)         ; overflow: keep E142 at 0xFF
BF93  RET

; ── sub-entries reached by JP ──
BF94  CALL 0x4496           ; every-16th: allocate slot
BF97  JR C, 0xBF9A
BF99  LD (HL), 0x3D         ; write type 61 (0x3D) to slot

BFA0  CALL 0x4496           ; trigger: allocate slot
BFA3  RET C
BFA4  RES 0,(IX+0x25)       ; clear E125 bit0 (trigger consumed)
BFA8  LD (HL), 0x44         ; write type 68 (0x44 = ground structure)
BFAA  RET
```

## 0xE100 game-state fields used by this routine

| Offset | Address | Name | Usage |
|--------|---------|------|-------|
| +0x02 | 0xE102 | status_flags | Bit 3 = global spawn block |
| +0x25 | 0xE125 | spawn_trigger | Bit 0 = spawn type-44 immediately (set by stream; cleared by BFA4) |
| +0x26 | 0xE126 | stream_slot_ctr | Counts mod 16; every 16th spawn gets type 0x3D |
| +0x2D | 0xE12D | spawn_ctrl | Bit 0 = call 0xBE27; Bit 1 = stream active; Bit 3 = stream block |
| +0x2E | 0xE12E | spawn_pos_hi | High byte of 16-bit spawn position accumulator |
| +0x2F | 0xE12F | spawn_pos_lo | += 8 per entity spawned; carry → spawn_pos_hi |
| +0x33 | 0xE133 | spawn_table_ptr | 16-bit LE pointer into ROM level entity-type sequence |
| +0x35 | 0xE135 | spawn_subtable_ctr | Sub-table counter reset logic |
| +0x37 | 0xE137 | spawn_timer | Countdown; reloaded from spawn_timer_reload |
| +0x38 | 0xE138 | spawn_timer_reload | Reload value for spawn_timer |
| +0x42 | 0xE142 | spawn_event_ctr | Incremented per entity spawned; saturates at 0xFF |

## Spawn table format (at 0xE133 pointer)

A sequence of entity type bytes (e.g. at 0xBECF during normal gameplay):
`2C 2C 38 38 2C 0C 0A 0D 0A 0E 0F 0A 0A 39 0B 30 …`

Types observed: 44 (ground structure), 56 (box/pickup), 10–15 (enemies), 57, 11
(base projectile spawner), 48 (ground-structure projectile). Type 0 = end of table.

## Notes

- The "base entity" is NOT a separate entity type. The base encounter is a
  composition: `place_tile_group` (write 0xE150=1 and populate 0xE71E),
  type-35 (eye animation), type-11 (projectile spawn), type-80 (hit handler),
  types 73–79 (base-gated entities).
- `0xBECF` (current spawn table address) is in the 0xBExx area — decompressed
  RAM or high ROM; needs further investigation.
- `0xBE27` (called when 0xE12D bit0 set) computes scroll-position offsets using
  0xE12E, 0xE132, and a lookup table at 0xBE7C. Its full role is not yet decoded.
