---
address: 0x8501
end: 0x8524
kind: routine
name: handler_type38_burst_fragment
confidence: confirmed
inputs:  { IX: "entity slot" }
outputs: {}
clobbers: [AF, BC, DE, HL]
calls:   [0x4cf7, 0x4898, 0x44a6]
called_by: [0x445f]
tags: [entity, enemy, fragment]
sprint: "0050"
---

# handler_type38_burst_fragment

**Type 38** — burst fragment. Like the lead bullet but flies in a fixed
direction taken from its `+0x1a` spawn param instead of aiming at the player.
Spawned in groups (7× by type-7 umber, by ground-gun pairs, by luster/swooper).

```
8501  BIT 7,(IX+0x00) / JR NZ,0x84fb         ; active → entity_update + post (shared with type 37)
8507  LD (IX+0x17),0x03
850b  LD (IX+0x0c),0x03                         ; bflags = Y + X motion
850f  LD (IX+0x03),0x1c                          ; pattern 7
8513  LD (IX+0x04),0x8f                           ; colour white
8517  LD A,(IX+0x1a) / AND 0x0f / LD E,A           ; direction = spawn param & 0x0F
851d  CALL 0x4cf7                                   ; set_velocity_from_dir(E)
8520  SET 7,(IX+0x00) / RET
```

`+0x1a` is the per-fragment value written by the spawner; for the umber burst it
comes from [[umber_burst_param_table]].

## Related

[[set_velocity_from_dir]], [[handler_type37_lead_bullet]] (shares active tail
0x84fb), [[umber_burst_param_table]], [[entity_jump_table]].
