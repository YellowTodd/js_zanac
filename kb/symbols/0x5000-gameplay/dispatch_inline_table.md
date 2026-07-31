---
address: 0x5c2e
end: 0x5c3b
kind: routine
name: dispatch_inline_table
confidence: confirmed
inputs:  { A: "index into the inline word-table that follows the CALL" }
outputs: {}
clobbers: []
calls: []
called_by: [0x5CF5, 0x7266, 0x727c, 0x74ab, 0x8C1A, 0x8D19, 0x94E8]
sprint: "0037"
tags: [dispatch, jump-table, helper]
---

# dispatch_inline_table

## Summary

Computed-jump helper. The caller does `CALL 0x5c2e` immediately followed by a
word-table of target addresses; this routine reads the return address off the
stack (= table base), indexes it by **A×2**, loads the word, and `RET`s to that
target — effectively `JP (table[A])` while preserving all registers (DE is saved
and restored; HL is swapped through the stack).

```
EX (SP),HL      ; HL = table base (the inline data after the CALL)
PUSH DE; ADD A,A; LD E,A; LD D,0; ADD HL,DE
LD E,(HL); INC HL; LD D,(HL)    ; DE = table[A]
EX DE,HL; POP DE; EX (SP),HL    ; put target on stack, restore HL
RET                              ; -> target[A]
```

## Users (dual-use across the engine)

A single generic jump-table trampoline reused by four subsystems:

| Caller | Inline table | Role |
|--------|--------------|------|
| 0x5CF5 | 0x5CF8 (3 entries) | [[decompress_block]] double-special command (STOP / SET-SPECIAL / MULTI) |
| 0x94E8 | 0x94EB `map_cmd_jump_table` (13 entries) | [[map_script_step]] map-command dispatch — see [[level_script_format]] |
| 0x7266, 0x727C, 0x74AB | fire tables | 3-phase fire-weapon dispatch ([[fire-weapon-dispatch]]), on `fire_num` (E14B) |
| 0x8C1A, 0x8D19 | enemy sub-tables | enemy handler dispatch (subsystem G) |

## Confirmed (sprint 0048)

Planting `fire_num` and running from each call site landed on the expected
handler from the inline table. `tools/sprint0048_verify.py`.
