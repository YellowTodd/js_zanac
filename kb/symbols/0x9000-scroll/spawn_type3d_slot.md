---
address: 0xBF94
end: 0xBF9B
kind: routine
name: spawn_type3d_slot
confidence: confirmed
inputs:  {}
outputs: {}
clobbers: [AF, HL]
calls:   [0x4496]
called_by: [0xBF2C]
tags: [entity, spawn, ground-structure]
sprint: "0029"
---

# spawn_type3d_slot

## Summary

Every-16th-spawn special case of `ground_struct_spawn_ctrl`. Reached by
`JP Z, 0xBF94` (0xBF5D) when `stream_slot_ctr` (0xE126) mod 16 == 0: allocates a
free entity slot and writes entity type `0x3D` (61) into it.

## Analysis

```
BF94  CALL 0x4496        ; alloc_entity_slot → HL = free slot, CF set if none
BF97  JR C, 0xBF9B       ; no slot: bail
BF99  LD (HL), 0x3D      ; write entity type 0x3D (61)
BF9B  RET
```

Counterpart of the normal table-driven spawn path in
`ground_struct_spawn_ctrl` (0xBF2C) and the immediate type-0x44 trigger
`sub_bfa0` (0xBFA0).
