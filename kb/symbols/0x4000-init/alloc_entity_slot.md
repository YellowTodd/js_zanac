---
address: 0x4496
end: 0x44A5
kind: routine
name: alloc_entity_slot
confidence: confirmed
inputs:  {}
outputs: { HL: "free slot address (if CF=0)", CF: "set = no free slot" }
clobbers: [AF, BC, DE, HL]
calls:   []
called_by: [0x71DA, 0x71DB]
tags: [entity, spawn]
sprint: "0014"
---

# alloc_entity_slot

## Summary

Scans entity slots 5–25 (the ground-structure/enemy pool at 0xE3A0–0xE620,
stride 32) for the first slot whose type byte is 0 (inactive). Returns
HL pointing to that slot with carry clear. If all 21 slots are occupied,
sets carry and returns — the caller is responsible for handling failure.

## Analysis

```
4496  LD HL, 0xE3A0      ; first candidate = slot 5
4499  LD DE, 0x0020      ; stride = 32 bytes per slot
449C  LD B, 0x15         ; 21 iterations (slots 5–25)
449E  LD A, (HL)         ; read type byte
449F  OR A
44A0  RET Z              ; type == 0 → free slot found; return HL, CF=0
44A1  ADD HL, DE         ; advance to next slot
44A2  DJNZ 0x449E        ; loop
44A4  SCF                ; all 21 slots occupied
44A5  RET                ; return CF=1 (failure)
```

## Notes

- **Slots 0–4 are never scanned.** They are permanently reserved: slot 0 for
  the player ship, slots 1–4 for player-controlled projectiles (managed by
  dedicated code that does not use this allocator).
- Slots 5–25 are the shared pool for ground structures, enemies, and base entities.
- First-fit allocation: returns the lowest-numbered free slot. No priority ordering.
- `spawn_col_marker` (0x71DA) calls this to obtain a slot for a new type-39
  column marker. Entity handlers that self-spawn children (type 11 → type 69,
  type 21 spawning sub-type) also call it.
