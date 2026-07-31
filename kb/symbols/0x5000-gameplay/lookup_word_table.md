---
address: 0x51E6
end: 0x51EF
kind: routine
name: lookup_word_table
confidence: confirmed
inputs: { A: "table index", BC: "table base address" }
outputs: { HL: "16-bit word at BC + 2*A", A: "low byte" }
clobbers: [AF, HL]
called_by: [0x4F4A, 0x5099, 0x513F, 0x5199]
tags: [audio, psg, sound-engine, helper]
sprint: "0028"
---

# lookup_word_table

## Summary

Generic helper: returns the little-endian 16-bit word at `BC + 2*A` in HL. Used
throughout the sound engine to index word-pointer tables (event table 0x5234,
command jump table 0x4F6C, volume-curve table 0x527D, frequency base table
0x51F0).

## Analysis

```
51E6  ADD A,A          ; A = 2*index   (entry 0x51E7 is used with A already 2*idx)
51E7  LD H,0; LD L,A
51EA  ADD HL,BC        ; HL = BC + offset
51EB  LD A,(HL); INC HL; LD H,(HL); LD L,A   ; HL = word(BC+offset)
51EF  RET
```

Note the two entry points: **0x51E6** doubles A first (word index); **0x51E7**
is entered when the caller already holds a byte offset in A (e.g. `play_note`
duration-table lookup at 0x5055, single-byte table).
