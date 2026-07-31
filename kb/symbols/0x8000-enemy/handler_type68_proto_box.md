---
address: 0x77a1
end: 0x77e9
kind: routine
name: handler_type68_proto_box
confidence: confirmed
inputs:  { IX: "entity slot" }
outputs: {}
clobbers: [AF, BC, DE, HL]
calls:   [0x43c0, 0x77e0, 0x4496]
called_by: [0x445f]
tags: [entity, enemy, box, spawner]
sprint: "0051"
---

# handler_type68_proto_box

**Type 68** — box-cluster spawner. Spawns a row of **3 boxes** at incrementing X,
with per-box type from [[proto_box_type_table]] (0x77ea, indexed by `data_e104`)
and per-box sprite/param from [[proto_box_sat_table]] (0x7808, indexed by
`data_e105` high nibble). (Earlier guessed as a single type-4 converter — it is a
3-box layout spawner; each child becomes a box of type 4/5/6, see
[[handler_type4_box]].)

```
77a1  CALL 0x43c0 / LD A,H / AND 0x3f / ADD A,0x38 / EX AF,AF'  ; base X (random) → A'
77aa  LD A,(0xe104) / LD HL,0x77ea / CALL 0x77e0 / EX DE,HL     ; DE = &type_table[e104&0xf ×3]
77b4  LD A,(0xe105) / RLCA×4 / LD HL,0x7808 / CALL 0x77e0       ; HL = &sat_table[e105hi ×3]
77c1  EXX / LD C,0x03 / PUSH IX                                  ; loop 3 boxes
77c6  (loop) POP BC=slot; (BC+0)=type from (DE)++; (BC+2)=X (A'), A'+=0x20; (BC+3)=sat from (HL)++
77d6  EXX / DEC C / RET Z / CALL 0x4496 / RET C / PUSH HL / JR loop
; helper 0x77e0:  A&=0x0f; HL += A*3; RET   (3-byte stride index)
```

## Related

[[proto_box_type_table]] (0x77ea), [[proto_box_sat_table]] (0x7808),
[[handler_type4_box]], [[entity_jump_table]] (68).
