---
address: 0x8668
end: 0x869d
kind: routine
name: handler_type20_lead_homing
confidence: confirmed
inputs:  { IX: "entity slot" }
outputs: {}
clobbers: [AF, BC, DE, HL]
calls:   [0x43c0, 0x4898, 0x44a6]
called_by: [0x445f, 0x79fb]
tags: [entity, enemy, lead, homing]
sprint: "0050"
---

# handler_type20_lead_homing

**Type 20** — lead pellet that Y-homes toward the bottom of the screen with a
randomised horizontal drift. Spawned by the type-9 umber timer ([[handler_type7_umber]]).

```
8668  BIT 7,(IX+0x00) / JR NZ,0x8698        ; active → update + post
866e  LD (IX+0x03),0x1c                      ; pattern 7
8672  LD (IX+0x04),0x8f                       ; colour white
8676  LD (IX+0x0c),0x0b                        ; bflags = Y + X motion + Y-homing
867a  LD (IX+0x13),0xff                        ; tgt_y = 255 (homes to bottom, off-screen)
867e  LD (IX+0x15),0x0c                         ; y_accel = 12
8682  LD (IX+0x17),0x01
8686  CALL 0x43c0                               ; prng_next → HL
8689  LD A,H / AND 0x03 / SUB 0x02 / LD (IX+0x0b),A  ; vx ∈ {-2,-1,0,+1}
8691  LD (IX+0x0a),L                             ; vx_frac = random
8694  SET 7,(IX+0x00)
8698  CALL 0x4898 / JP 0x44a6                    ; entity_update + entity_post
```

## Related

[[prng_next]] (0x43c0), [[handler_type7_umber]] (spawner), [[entity_jump_table]].
