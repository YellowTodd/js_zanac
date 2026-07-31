---
address: 0x84dd
end: 0x8500
kind: routine
name: handler_type37_lead_bullet
confidence: confirmed
inputs:  { IX: "entity slot" }
outputs: {}
clobbers: [AF, BC, DE, HL]
calls:   [0x4c8b, 0x4898, 0x44a6]
called_by: [0x445f]
tags: [entity, enemy, bullet]
sprint: "0050"
---

# handler_type37_lead_bullet

**Type 37** — enemy lead bullet aimed at the player. Init snapshots the player
position ([[player_pos_snapshot]] 0x4c8b) so the motion fields point toward it.
Pattern 0x1c (pat 7). Fired by veybar (type 22) and luster (type 18).

```
84dd  BIT 7,(IX+0x00) / JR NZ,0x84fb         ; active → update
84e3  LD (IX+0x17),0x03
84e7  LD (IX+0x03),0x1c                         ; pattern 7
84eb  LD (IX+0x04),0x8f                          ; colour white
84ef  LD (IX+0x0c),0x03                           ; bflags = Y + X motion
84f3  CALL 0x4c8b                                  ; player_pos_snapshot → aim
84f6  SET 7,(IX+0x00) / RET
84fb  CALL 0x4898 / JP 0x44a6                       ; entity_update + entity_post
```

## Related

[[player_pos_snapshot]], [[handler_type22_veybar]], [[handler_type16_luster]],
[[handler_type38_burst_fragment]], [[entity_jump_table]].
