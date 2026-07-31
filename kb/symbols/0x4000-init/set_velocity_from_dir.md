---
address: 0x4cf7
end: 0x4d41
kind: routine
name: set_velocity_from_dir
confidence: confirmed
inputs:  { E: "direction 0-15 (clockwise from 'down')", IX: "entity slot", "(IX+0x17)": "speed: bits0-5 = step count, bit6/bit7 = ×2/×4 prescale" }
outputs: { "(IX+0x08/09)": "Y velocity (16-bit signed, fixed-point)", "(IX+0x0a/0b)": "X velocity" }
clobbers: [AF, BC, DE, HL]
calls: []
called_by: [0x72db, 0x736f, 0x7625, 0x7372]
sprint: "0048"
tags: [velocity, entity, player, weapon, fire, vector]
---

# set_velocity_from_dir

## Summary

Shared helper that turns a 16-way **direction index** (E) plus a per-entity
**speed** (IX+0x17) into a 16-bit fixed-point velocity vector, written to the
entity slot at IX+8/9 (X) and IX+0a/0b (Y). Used by the player ship
([[player_ship_update]] via the [[xvel_table]]), the fire weapons
([[fire_weapon_handler]]), and entity handlers. Reads the unit-vector table
[[vel_dir_table]] (0x4d65).

> **CLAUDE.md correction:** the 0x4cf7–0x4da4 block was listed as a
> "vertical-collision distance table (purpose known, no KB file)". It is in fact
> this routine (code, was stored as a `DB` block) followed by three data tables:
> `dir_angle_thresholds` (0x4d42), `dir_remap_table` (0x4d45), and
> [[vel_dir_table]] (0x4d65). Disassembled + labelled in sprint 0048.

## Analysis (0x4cf7–0x4d41)

```
LD A,E; ADD A,A; ADD A,A      ; E*4 (4-byte table stride)
LD HL,0x4d65; ADD HL,DE       ; -> vel_dir_table[dir]
LD E,(HL)/D,(HL+1)            ; DE = Y unit-component (signed word)
LD C,(HL+2)/B,(HL+3)          ; BC = X unit-component
LD A,(IX+0x17)                ; speed byte
BIT 6,A -> ADD HL,HL/ADD HL,BC ; ×2 prescale of the base vector (per axis)
BIT 7,A -> ×4 prescale
AND 0x3f; LD B,A              ; B = repeat count (low 6 bits of speed)
PUSH HL; LD HL,0; (DJNZ ADD HL,DE) ; X = DE * count -> IX+8/9
POP DE;  LD HL,0; (DJNZ ADD HL,DE) ; Y = (prescaled Y) * count -> IX+0a/0b
RET
```

Net: `vel = unit_vector(dir) << prescale(bit6/7) × count(bits0-5)`.

## Axis-order correction (2026-07-30)

The entry pair is **(Y, X)**, not (X, Y): the first word is written to
IX+0x08/0x09, which [[entity_table]] documents as the Y velocity
fraction/integer, and the second to IX+0x0a/0x0b (X). This entry previously had
the two labelled the other way round, which mirrors every direction.

Cross-checking against the player's steering settles it. `read_player_input`
(0x43A0) seeds the selector at 4 and applies +1 up, −1 down, −3 left, +3 right;
[[xvel_table]] maps that selector to a direction index. Under (Y, X):

| Held | selector | xvel_table | vel_dir_table | result |
|------|----------|-----------|---------------|--------|
| up | 5 | 12 | (−128, 0) | up ✓ |
| down | 3 | 4 | (+128, 0) | down ✓ |
| left | 1 | 8 | (0, −128) | left ✓ |
| right | 7 | 0 | (0, +128) | right ✓ |
| up+right | 8 | 14 | (−90, +90) | up-right ✓ |
| down+left | 0 | 6 | (+90, −90) | down-left ✓ |

All eight agree. Under (X, Y) every one of them is mirrored — holding up would
move the ship left.

## Live confirmation (sprint 0048)

Micro-exec with IX = scratch slot, IX+0x17 = 1 (count 1, no prescale), E = dir:
IX+8/9 and IX+0a/0b matched `vel_dir_table[dir]` exactly for dirs 0/2/4/6/8/12.
(The raw pairs quoted there were right; only the axis labelling was wrong — dir
0 is (0, +128) = **right**, dir 4 is (+128, 0) = **down**.)
`tools/sprint0048_verify.py`.
