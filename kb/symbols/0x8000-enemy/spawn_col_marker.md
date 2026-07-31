---
address: 0x71DA
end: 0x71F5
kind: routine
name: spawn_col_marker
confidence: confirmed
inputs:  { IX: "parent entity slot" }
outputs: { HL: "new marker slot address (if allocated)", CF: "set = allocation failed" }
clobbers: [AF, BC, DE, HL]
calls:   [0x4496]
called_by: [0x7826, 0x7E9C, 0x7F99, 0x82D0]
tags: [entity, ground-structure, spawn]
sprint: "0012"
---

# spawn_col_marker

## Summary

Allocates a free entity slot, writes type 0x27 (column marker) and color 0x81
into it, then stores the slot address into the parent entity's `child_ptr`
field (+0x1B/+0x1C). Called during ground-structure entity initialisation to
create the invisible occupancy marker that `check_col_clear` (0x9B22) later
scans when deciding whether a new structure can be placed.

## Analysis

```
71DA  PUSH DE
71DB  CALL 0x4496        ; allocate free entity slot → HL = slot address
71DE  JR C, 0x71F1       ; if carry (no free slot) → fail
71E0  LD (IX+0x1B), L    ; child_ptr_lo ← L
71E3  LD (IX+0x1C), H    ; child_ptr_hi ← H  (parent → marker link)
71E6  LD (HL), 0x27      ; marker type byte = 39 (col marker)
71E8  LD DE, 0x0004
71EB  ADD HL, DE
71EC  LD (HL), 0x81      ; marker +4 (color/flags) = 0x81
71EE  DEC HL
71EF  POP DE
71F0  RET
71F1: [fail path — POP DE, RET with CF set]
```

## Notes

- The allocated slot's type byte is set to 0x27 directly; no separate init call.
- Only the type (+0) and one flag byte (+4) are initialised here. The countdown
  at +0x18 and the forward pointer at +0x1B/+0x1C are left to the caller.
- Type-39 column markers spawned this way are scanned by `check_col_clear` via
  their address in the entity table (stride 32 from slot 25 down to slot 5).
- `0x4496` is the free-slot allocator; it scans the entity table for type=0 slots.
