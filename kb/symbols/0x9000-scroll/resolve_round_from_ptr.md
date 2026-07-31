---
address: 0x9444
end: 0x945B
kind: routine
name: resolve_round_from_ptr
confidence: confirmed
inputs:
  HL: a stream-start pointer (typically E722, the next stage's stream start)
outputs:
  A: round number 1–8, or 0 if HL is below the round-1 entry (ending)
clobbers: [AF, B, DE]
calls: []
called_by: [0x40ED, 0x9436]
tags: [round, level-transition, state-machine, table-search]
sprint: "0045"
---

# resolve_round_from_ptr

## Summary

Maps a level **stream-start pointer** to its **round number** by linear-searching
`stage_stream_ptr_table` (0x945C). Used by the stage-transition path: when a stage
is cleared the scroll engine puts the next stage's stream start in `E722`;
`level_complete_handler` (via `SUB_ram_9433`, 0x9436) calls this to derive the new
round number, which is written to `E701` (the round selector).

## Analysis (source 0x9444–0x945B)

```
9444  PUSH HL
9445  LD HL,0x945C       ; stage_stream_ptr_table
9448  LD B,8             ; 8 rounds
944A  LD E,(HL); INC HL; LD D,(HL); INC HL   ; DE = table[i]
944E  EX (SP),HL; PUSH HL                     ; HL = input ptr
9450  AND A; SBC HL,DE                        ; input - table[i]
9453  POP HL; EX (SP),HL                      ; restore table cursor
9455  JR NC,0x9459       ; input >= table[i] -> match, return B
9457  DJNZ 0x944A        ; else next entry
9459  LD A,B             ; A = round number (B at match; 0 if exhausted)
945A  POP HL
945B  RET
```

The table is **descending** by address; `B` counts 8→1 as it scans, so the entry
that the input pointer first reaches-or-exceeds gives the round. Entry *i* holds
round `8−i`'s stream start, so `A = 8−i = round`. If the pointer is below every
entry (i.e. below round 1's start), `DJNZ` exhausts `B` to 0 and `A = 0`.

## Live confirmation (sprint 0045)

Micro-exec for every table entry returns its round exactly:

| HL | → A | HL | → A |
|----|-----|----|-----|
| 0xB7A5 | 8 | 0xAD61 | 3 |
| 0xB61A | 7 | 0xAAEF | 2 |
| 0xB3FD | 6 | 0xA751 | 1 |
| 0xB1DE | 5 | 0xA6F4 (ending) | 0 |
| 0xAF1F | 4 | | |

The ending pointer **0xA6F4** (`E722` set to it by the scroll engine after the
final boss) resolves to round **0**, the value seen in `E701` once the ending
fires. `tools/sprint0045_verify.py`.

## See also

- `stage_stream_ptr_table.md` — 0x945C, the table searched here.
- `level_complete_handler.md` — 0x40DA, the stage-transition caller.
- `round-progression.md` (guide) — how rounds advance and the end-of-game path.
