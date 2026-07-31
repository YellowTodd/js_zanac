---
address: 0xBFA0
end: 0xBFAA
kind: routine
name: sub_bfa0
confidence: confirmed
inputs:
  IX: "game_state_block (0xE100)"
outputs: {}
clobbers: [AF, HL]
calls:   [0x4496]
called_by: []
tags: [base, gamestate, entity, spawn]
sprint: "0029"
---

# sub_bfa0 — Spawn-trigger entity allocator

## Summary

Part of a cluster of small base-encounter subroutines packed at 0xBFA0–0xBFF4.
This file covers **SUB_bfa0** itself (the type-0x44 spawn trigger). The
adjacent encounter-counter mutators and the shared display tail now have their
own entries: [[inc_encounter_a]] (0xBFAB), [[dec_encounter_a]] (0xBFB3),
[[dec_encounter_b]] (0xBFBF), [[dec_encounter_inner]] (0xBFC2),
[[inc_encounter_inner]] (0xBFCB), and `base_encounter_ctrl` (0xBFD6 display tail).

## SUB_bfa0 (0xBFA0) — spawn-trigger entity allocator

```
BFA0  CALL 0x4496        ; alloc_entity_slot → HL = free slot (0xE3A0–0xE620)
BFA3  RET C              ; return if no slot available
BFA4  RES 0, (IX+0x25)  ; clear spawn_trigger (0xE125) bit 0  [IX=0xE100]
BFA8  LD (HL), 0x44      ; write entity type 0x44 (= 68 decimal) into slot
BFAA  RET
```

Called when spawn_trigger (0xE125) bit 0 is set. Allocates a free entity slot
and populates it with type 68 (handler 0x77A1). No CALL 0xBFA0 found in ROM —
likely reached via indirect dispatch or RST.

The adjacent routines (0xBFAB–0xBFD5) and the shared 0xBFD6 HUD-display tail are
documented in their own files — see the links in the Summary above and
`base_encounter_ctrl.md`. The display tail writes 0xE12E / 0xE132 / 0xE130 to
the VDP name table (base-encounter HUD readout) via WRTVRM.

## Notes

- SUB_bfa0 is the only place that writes entity type 0x44 (hex) = 68 decimal
  to an entity slot. This was previously labelled "unknown" in entity_jump_table.
  Its role in the base-encounter chain is not yet fully understood.
- The "near 0xBFA0, uses (IX+0x25)" note from sprint 0010 is now confirmed:
  IX+0x25 = 0xE125 = spawn_trigger when IX = 0xE100.
