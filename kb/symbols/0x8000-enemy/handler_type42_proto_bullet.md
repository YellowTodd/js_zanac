---
address: 0x85cc
end: 0x85ed
kind: routine
name: handler_type42_proto_bullet
confidence: confirmed
inputs:  { IX: "entity slot" }
outputs: {}
clobbers: [AF]
calls:   [0x84e3, 0x8507]
called_by: [0x445f]
tags: [entity, enemy, bullet, fragment]
sprint: "0051"
---

# handler_type42_proto_bullet

**Types 42 and 43** — "scattered" variants of the bullet/fragment. They run the
normal init body of their base type, remap to the *active* base type, then
randomise the velocity fields (XOR with R) so each one flies off in a slightly
different direction.

| Type | Entry | Inits as | Becomes |
|------|-------|----------|---------|
| 42 | 0x85cc | type 37 init (0x84e3, lead bullet) | 0xA5 = active type 37 |
| 43 | 0x85d6 | type 38 init (0x8507, burst fragment) | 0xA6 = active type 38 |

```
; type 42:
85cc  CALL 0x84e3 / LD (IX+0x00),0xa5 / JP 0x85dd
; type 43:
85d6  CALL 0x8507 / LD (IX+0x00),0xa6
; shared velocity scatter (0x85dd):
85dd  LD A,R / XOR (IX+0x0a) / LD (IX+0x0a),A   ; scramble vx_frac
85e5  LD A,R / XOR (IX+0x08) / LD (IX+0x08),A   ; scramble vy_frac
85ed  RET
```

## Related

[[handler_type37_lead_bullet]] (0x84e3 init), [[handler_type38_burst_fragment]]
(0x8507 init), [[entity_jump_table]] (42, 43).
