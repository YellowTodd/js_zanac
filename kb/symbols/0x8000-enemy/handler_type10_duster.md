---
address: 0x7a2a
end: 0x7a66
kind: routine
name: handler_type10_duster
confidence: confirmed
inputs:  { IX: "entity slot" }
outputs: {}
clobbers: [AF, BC, DE, HL]
calls:   [0x71da, 0x71c5, 0x4898, 0x71f6, 0x44ba]
called_by: [0x445f]
tags: [entity, enemy, duster]
sprint: "0049"
---

# handler_type10_duster

## Summary

Handler for **type 10**, the *duster*: spawns at a random X, falls (vy=3) while
homing horizontally toward the player's side. Pattern 0x58 (pat 22), colour
0x89. Confirmed in [[entity_jump_table]].

## Decode

```
7a2a  BIT 7,(IX+0x00) / JP NZ, 0x79ae    ; active → entity_update + post
7a31  CALL 0x71da / LD (HL),0x5c          ; spawn_col_marker, complement = 0x5C (duster_compl)
7a36  CALL 0x71c5                         ; random_x_pos → A = random X, stored to +0x02
7a39  LD (IX+0x14), 0x00
7a3d  CP 0x88 / JR NC,0x7a44 / DEC (IX+0x14)  ; X<136 → +0x14 = 0xFF (home toward right)
7a44  LD (IX+0x03), 0x58    ; pattern 22
7a48  LD (IX+0x04), 0x89    ; colour
7a4c  LD (IX+0x0c), 0x13    ; bflags = Y + X-motion + X-homing
7a50  LD (IX+0x08), 0x00    ; vy_frac = 0
7a54  LD (IX+0x09), 0x03    ; vy = +3 (down)
7a58  LD (IX+0x16), 0x08    ; x_accel = 8
7a5c  LD (IX+0x17), 0x01
7a60  SET 7,(IX+0x00)
7a64  JP 0x79ae             ; entity_update + entity_post (shared umber tail)
```

`+0x14` sign selects the X-homing direction from the spawn X: spawned on the
left half (X<136) → homes right, else homes left, so it always drifts toward
screen centre / the player.

## Related

[[handler_type7_umber]] (shares the 0x79ae update+post tail), [[spawn_col_marker]],
[[random_x_pos]] (0x71c5), [[entity_jump_table]].
