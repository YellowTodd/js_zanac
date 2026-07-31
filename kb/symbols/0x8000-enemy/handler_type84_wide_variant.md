---
address: 0x8eb7
end: 0x8f24
kind: routine
name: handler_type84_wide_variant
confidence: confirmed
inputs:  { IX: "entity slot" }
outputs: {}
clobbers: [AF, BC, DE, HL]
calls:   [0x8f25, 0x4496, 0x8ddb]
called_by: [0x445f]
tags: [entity, enemy, base, ground-structure]
sprint: "0052"
---

# handler_type84_wide_variant

**Types 84–86** — wide-structure variant. Gates on [[wide_struct_init]] (0x8f25)
like the wide structure, then joins the wide-structure body at 0x87c3 with a
preset +0x1c/+0x1d. Its active body (0x8ec7) is a **wave spawner**: on a +0x1c
countdown it emits child entities — type 0x15 (=21, light_bar) or 0x26 (=38,
burst fragment) — in cycling X spreads, and aims part of the spread at the player
(reads 0xe302 / 0xe710).

```
8eb7  CALL 0x8f25 / JR C,0x8ec7
8ebc  LD (IX+0x1c),0x03 / (IX+0x1d),0x18 / JP 0x87c3   ; → wide-structure body
; active (0x8ec7):
8ec7  DEC (IX+0x1c) / JP NZ,0x8806                      ; countdown → just post
8ecd  reload +0x1c from +0x1d / find_free_slot / branch by type (0xd4/0xd5):
8ee3   spread A: C = ((+0x1e)&3)*4+2 ; A=0x15 ; spawn_entity        ; light_bar wave
8efc   (aim variant: compare 0xe302, check 0xe710)
8f13   spread B: C = ((+0x1e)*2)&0x0f ; A=0x26 ; spawn_entity        ; fragment wave
```

## Related

[[handler_type70_wide_structure]] (0x87c3 body), [[wide_struct_init]] (0x8f25),
[[spawn_entity]] (0x8ddb), [[entity_jump_table]] (84–86).
