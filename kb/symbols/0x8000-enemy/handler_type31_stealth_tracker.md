---
address: 0x7F73
end: 0x8012
kind: routine
name: handler_type31_stealth_tracker
confidence: confirmed
inputs:  { IX: "entity slot" }
outputs: {}
clobbers: [AF, BC, DE, HL]
calls:   [0x71DA, 0x4CF7, 0x730B, 0x48B8]
called_by: [0x445F]
tags: [entity, enemy, stealth-jet, player-tracking]
sprint: "0026"
---

# handler_type31_stealth_tracker

## Summary

Shared handler for types 31, 33, 34, 65, and 66 (three entry points).
Types 31 and 33 track the player's Y coordinate each frame, closing in
with a fixed velocity, then switching to X-motion once aligned. The sprite
is the stealth pattern (pattern 51, sat=0xCC), making it nearly invisible.

## Entry points

| Type(s) | Entry | Behaviour |
|---------|-------|-----------|
| 31, 33  | 0x7F84 | Player-Y tracking (running code first, init on first call) |
| 34, 65, 66 | 0x7F99 | Init check only; running code at 0x8012 (no Y-tracking) |

## Handler decode (0x7F84–0x7FFB)

### Running path — types 31/33 (0x7F84)

```
7F84  LD A,(0xE301)         ; A = player Y (slot 0 byte 1)
7F87  CP (IX+0x01)          ; compare with entity Y
7F8A  BIT 6,(IX+0x05)       ; test "above player" flag
7F8E  JR Z, 0x7F91          ; if bit6=0, skip
7F90  CCF                   ; complement carry (reverse direction)
7F91  JR NC, 0x7F73         ; player Y > entity Y → Y-motion update (0x7F73)
7F93  LD (IX+0x0C), 0x02    ; player Y ≤ entity Y → switch to X-motion
7F97  JR 0x7F73             ; → update
```

Code at **0x7F73** (not shown): applies current velocity using entity_update
via bit0 (Y-motion) or bit1 (X-motion) after the handler sets +0x0C.

### Init check (0x7F99, entry for types 34/65/66 and fallthrough for 31/33)

```
7F99  BIT 7,(IX+0x00)       ; already initialized?
7F9D  JP NZ, 0x8012         ; yes → running code for types 34/65/66
```

### Init body (0x7FA0, shared by all types)

```
7FA0  CALL 0x71DA            ; alloc_entity_slot → HL = new col-marker slot
7FA3  LD (HL), 0xD0          ; col-marker sat_name = 0xD0 (pat52 = stealth_compl)
7FA5  LD A, R / AND 0x06     ; random 0/2/4/6 → one of 4 columns
7FAC  LD HL, 0x807C          ; X position + velocity table (4 × 2 bytes)
7FAF  ADD HL, DE             ; index by random
7FB0  LD A, (HL)             ; A = X position
7FB1  LD (IX+0x17), 0x01
7FB5  LD (IX+0x02), A        ; entity X = table[random]
7FB9  LD E, (HL+1)
7FBA  CALL 0x4CF7            ; set initial velocity from table param
7FBD  LD (IX+0x0C), 0x03    ; bits 0+1 — Y+X motion via entity_update
7FC1  LD (IX+0x03), 0xCC    ; sat_name = 0xCC → pattern 51 (stealth)
7FC5  LD (IX+0x04), 0x88    ; color = EC + 8 (dark grey)
7FC9  LD (IX+0x0D), 0x30    ; anim_tick countdown = 48
7FCD  LD (IX+0x1D), 0x30
7FD1  LD (IX+0x1E), 0x03
7FD5  LD (IX+0x19), 0x07
7FD9  SET 7,(IX+0x00)        ; activate
; type-specific overrides:
7FDD  LD A,(IX+0x00)
7FE0  CP 0xA2                ; type 34 active (0x22|0x80)?
7FE2  JR Z, 0x800E           ; → type34 override block
7FE4  CP 0xC1                ; type 65 active (0x41|0x80)?
7FE6  JR NZ, 0x7FFE          ; → shared continue
; type-65 overrides: color 0x85, different counters
```

### X-position tracking (sub-path within running code)

When switching to X-motion (bit1 of +0x0C), code at ~0x73A0:
```
73A0  LD E,(IX+0x0F) / LD D,(IX+0x10)
73A6  ADD HL,DE           ; advance 16-bit accumulator +0x0F:+0x10
73A7  LD (IX+0x0F),L / LD (IX+0x10),H  ; store back
73AD  LD A,(0xE302)       ; A = player X
73B0  CP 0x48 / …         ; clamp to [72, 167]
73BE  ADD A, H            ; entity X = clamped_playerX + accumulator_hi
73BF  LD (IX+0x02), A     ; update entity X
73C2  CALL 0x730B
73C5  JP 0x48B8           ; entity_post
```

## Sprite and motion

| Field | Value | Meaning |
|-------|-------|---------|
| +0x03 sat_name | 0xCC | Pattern 51 = stealth jet sprite (resembles a modern stealth fighter; fully visible in-game) |
| +0x04 sat_color | 0x88 | EC + 8 = dark blue-grey |
| +0x0C | 0x01→0x02 | bit0 = Y-motion (tracking player Y); switches to bit1 (X-motion) when aligned |
| +0x09 vy | 0x02 | +2 = moving downward toward player |

## Player-tracking mechanism

**Does NOT use entity_update bit3 Y-homing** (+0x13/+0x15/+0x17 are 0).
Instead, the handler at 0x7F84 manually:
1. Reads player Y from 0xE301 (= entity slot 0, byte 1)
2. Compares with entity's own Y (+0x01)
3. If player is below: leave +0x0C=0x01 (entity_update applies vy=+2 downward)
4. If player is at or above: set +0x0C=0x02 (switch to X-motion)

This creates a simple two-phase approach: close vertically, then flank horizontally.

## Table at 0x807C (spawn X + velocity param, confirmed)

4 entries × 2 bytes, selected by `R AND 0x06` (random 0/2/4/6):

| R & 0x06 | X | vel_param | Side |
|----------|---|-----------|------|
| 0 | 32 | 0x02 | Left |
| 2 | 208 | 0x06 | Right |
| 4 | 80 | 0x04 | Centre-left |
| 6 | 160 | 0x04 | Centre-right |

`vel_param` is passed as E to `CALL 0x4CF7` (velocity setter). Higher values
give stronger initial velocity. Types 31/33 spawn spread across four columns.

## Projectile direction tables (types 34/65/66 only)

| Address | Condition | Bytes | Meaning |
|---------|-----------|-------|---------|
| 0x8084 | player Y < entity Y | 0C 0A 0E | fire upward: Y_off=12, X_off=10 |
| 0x8087 | player Y ≥ entity Y | 04 02 06 | fire downward: Y_off=4, X_off=2 |

Type-34 fires IX+0x1E (=3) projectiles per burst at (entity_Y+Y_off, entity_X+X_off).

## Notes

- Col-marker (type 39) spawned via 0x71DA uses stealth_compl (pat 52, 0xD0)
  as its complement sprite — dark tint follows the entity.
- Sprint 0021 note "source lines 3262–3316 = player-tracker" was a
  misidentification; those lines are fire-weapon Field Shutter X-tracking
  code (fire type 2, 0x72F5–0x7330).
- Types 31/33 have **no init phase** in handler; pre-initialized at spawn.
- Type 34 fires audibly (SFX #21 via `SET 0,(IX+0x05)`); types 31/33 are silent.
- sub_730B (0x730B) is the fire weapon life-timer (used by fire types 5/7),
  NOT related to types 31–34 directly, but reachable from the same code area.
