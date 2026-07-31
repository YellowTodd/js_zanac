---
address: 0x8094
end: 0x816C
kind: routine
name: handler_type46_ground_projectiles
confidence: confirmed
inputs:  { IX: "entity slot (type 0x2E–0x37 with bit 7 = running flag)" }
outputs: {}
clobbers: [AF, BC, DE, HL]
calls:   [0x71DA, 0x71F6, 0x4898, 0x44BA, 0x816D, 0x4496]
called_by: [0x445F]
tags: [entity, base, projectile]
sprint: "0051"
---

# handler_type46_ground_projectiles

## Summary

Shared entity handler for types 46–55 (ten types, five pairs). These are
**ground-structure gun entities**: plane-shaped sprites (SAT_NAME 0x48) that
descend at vy≈1.3 and periodically spawn child projectiles at various angles.
Each pair shares one 4-byte subtable entry at 0x8189; the R register randomises
the spawn X-side (0x30 left / 0xC0 right) at init time.

## Subtable at 0x8189

Five entries × 4 bytes. Format: `[flags, SAT_COLOR, shoot_period, spawn_type]`.

The index is: `offset = ((type − 46) & 0xFE) × 2`.

| Offset | Types  | flags | SAT_COLOR | period | spawn_type |
|--------|--------|-------|-----------|--------|------------|
| +0     | 46/47  | 0x00  | 0x8F      | 32     | 0x26 → type 38 (burst_frag)   |
| +4     | 48/49  | 0x40  | 0x8D      | —      | 0x15 → type 21 (light_bar)    |
| +8     | 50/51  | 0x20  | 0x8A      | 80     | 0x26 → type 38 (burst_frag)   |
| +12    | 52/53  | 0x00  | 0x89      | 32     | 0x15 → type 21 (light_bar)    |
| +16    | 54/55  | 0x20  | 0x87      | 46     | 0x15 → type 21 (light_bar)    |

**Flags byte (stored at IX+0x05):**
- Bit 5 = oscillating sweep mode (angles 12 → 4 → 12, motion pauses during burst)
- Bit 6 = Y-tracking mode (compare player Y at 0xE301 to entity Y; fire when aligned)
- Bit 7 = tracking state latch (toggled by the Y-tracking logic)

## Init path (bit 7 of IX+0x00 = 0)

```
8094  BIT 7,(IX+0)         ; first-call check
8098  JR NZ, 0x80F8        ; running: skip init

809A  LD A,(IX+0)
809D  SUB 0x2E             ; A = type - 46  (0–9)
809F  AND 0xFE             ; pair two types together
80A1  ADD A, A             ; × 2  → subtable offset (0/4/8/12/16)
80A3  LD C, A  / LD B, 0
80A5  LD HL, 0x8189
80A8  ADD HL, BC           ; HL → subtable entry

80A9  LD B, 0x30           ; default X = 48  (left side)
80AB  LD DE, 0x0001        ; default D=0, E=+1
80AE  LD A, R
80B0  AND 0x01
80B2  JR Z, 0x80B9         ; if R bit 0 = 0: keep left / +1
80B4  LD B, 0xC0           ; X = 192 (right side)
80B6  LD DE, 0x08FF        ; D=8, E=0xFF (−1 step)

80B9  LD (IX+0x02), B      ; X coord (random left/right)
80BC  LD (IX+0x0C), 0x01   ; bflags = 0x01 (Y-motion only)
80C0  LD (IX+0x08), 0x50   ; vy_frac = 0x50
80C4  LD (IX+0x09), 0x01   ; vy = 1  → total vy ≈ 1.313 downward
80C8  LD (IX+0x03), 0x48   ; SAT_NAME = 0x48 (plane sprite, pat 18)

80CC  LD A,(HL)            ; subtable byte 0 = flags
80CF  LD (IX+0x05), A
80D0  BIT 5, A             ; oscillating mode?
80D2  JR Z, 0x80D7         ; no: keep D/B as initial angle/step
80D4  LD B, E              ; B = ±1  (E from DE above)
80D5  LD D, 0x0C           ; starting angle = 12

80D7  LD (IX+0x1D), D      ; angle accumulator
80DA  LD (IX+0x17), B      ; angle step (±1 for oscillating, large for straight)
80DD  INC HL
80DE  LD A,(HL)            ; byte 1 = SAT_COLOR
80DF  LD (IX+0x04), A
80E2  INC HL
80E3  LD A,(HL)            ; byte 2 = shoot_period
80E4  LD (IX+0x1E), A
80E7  LD (IX+0x18), A      ; countdown = shoot_period
80EA  INC HL
80EB  LD A,(HL)            ; byte 3 = spawn_type
80EC  LD (IX+0x1F), A
80EF  CALL 0x71DA          ; entity_post (apply SAT / register entity)
80F2  LD (HL), 0x50        ; write 0x50 to parent SAT_NAME field (via HL still advanced)
80F4  SET 7,(IX+0x00)      ; mark as running
```

## Running path (bit 7 = 1)

### Tracking mode (flags bit 6 set, types 48/49)

```
80F8  BIT 6,(IX+0x05)
80FC  JR Z, 0x811D         ; not tracking → countdown path
80FE  LD A,(0xE301)        ; player Y
8101  CP (IX+0x01)         ; compare to entity Y
8104  BIT 7,(IX+0x05)      ; latch bit
8108  JR Z, 0x8112
810A  JR C, 0x8164         ; player above: skip
810C  RES 7,(IX+0x05)
8110  JR 0x8164
8112  JR NC, 0x8164        ; player below: skip
8114  CALL 0x816D          ; fire! (spawn child entity)
8117  SET 7,(IX+0x05)
811B  JR 0x8164
```

### Countdown/oscillating mode (flags bit 6 clear)

```
811D  DEC (IX+0x18)        ; countdown
8120  JR NZ, 0x8164        ; not expired: skip

8122  LD A,(IX+0x1E)
8125  LD (IX+0x18), A      ; reload countdown
8128  LD A,(IX+0x1D)
812B  ADD A,(IX+0x17)      ; accumulate angle
812E  AND 0x0F             ; mask to 0–15
8130  LD (IX+0x1D), A
8133  CALL 0x816D          ; fire!

; Oscillating sweep check (flags bit 5):
8136  BIT 5,(IX+0x05)
813A  JR Z, 0x8164
813C  LD A,(IX+0x1D)
813F  CP 0x04              ; angle reached 4?
8141  JR Z, 0x814D
8143  LD (IX+0x18), 0x01   ; rapid-fire (every tick)
8147  LD (IX+0x0C), 0x00   ; disable Y-motion (entity pauses)
814B  JR 0x8164

814D  LD (IX+0x1D), 0x0C   ; reset angle to 12
8151  LD (IX+0x0C), 0x01   ; re-enable Y-motion
```

## Fire subroutine at 0x816D

Called by both tracking and countdown paths to spawn a child projectile.

```
816D  LD (IX+0x03), 0x4C   ; change own sprite to 0x4C ("muzzle flash")
8171  LD L,(IX+0x1B)
8174  LD H,(IX+0x1C)       ; HL = parent base-body entity address
8177  INC HL / INC HL / INC HL
817A  LD (HL), 0x54        ; set parent SAT_NAME[+3] = 0x54 (open/fire sprite)
817C  CALL 0x4496          ; find_free_slot → HL = new slot
817F  RET C                ; no free slot: abort
8180  LD A,(IX+0x1F)       ; A = spawn_type (0x26=38 or 0x15=21)
8183  LD C,(IX+0x1D)       ; C = current angle (0–15)
8186  JP 0x8DDB            ; entity_spawn_near_parent
```

**0x8DDB** sets: new_slot[0]=A (type), new_slot[+0x1A]=C (angle), copies
parent IX+0x01/IX+0x02 (Y/X) to new slot.

## Dispatch (0x8164)

After all branches, 0x8164 calls:
- `entity_update` (0x4898): applies motion per bflags
- `entity_post` (0x71F6): update SAT
- `entity_exit` (0x44BA): standard entity exit

## Notes

- IX+0x1B/+0x1C holds the parent base-body entity address; the fire subroutine
  modifies the parent's sprite (offset +3 within the parent slot) between 0x50
  (ready) and 0x54 (firing).
- The R-register random X-placement means the even/odd distinction within a
  pair (46/47, 48/49, …) does NOT control left vs right; both subtable entries
  are identical.
- "Oscillating" types pause their downward motion and rapid-fire from angle 12
  to 4 (a roughly 135° sweep), then resume descent.

## The subtable is mis-decoded in `zanac.asm` (2026-07-30)

The 20 bytes at 0x8189-0x819C are rendered as `NOP / ADC A,A / JR NZ / LD B,B /
...`, so `coverage_audit` classes them as code. The values above are correct
(re-dumped from the ROM), but any tool that filters the disassembly by
classification - such as the web port's data image - drops the whole table and
every one of these ten types loses its colour, fire period and projectile
type. Retained through `KEEP_RANGES` in `tools/export_assets.py`.
