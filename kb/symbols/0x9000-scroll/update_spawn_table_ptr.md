---
address: 0xBE27
end: 0xBE75
kind: routine
name: update_spawn_table_ptr
confidence: confirmed
inputs:  { IX: "game_state_block (0xE100)" }
outputs: {}
clobbers: [AF, BC, DE, HL]
calls:   []
called_by: [0xBF2C]
tags: [scroll, entity, spawn, ground-structure, level-map]
sprint: "0029"
---

# update_spawn_table_ptr

## Summary

Recomputes `ground_struct_spawn_ctrl`'s spawn parameters from the current
scroll position. Called from `ground_struct_spawn_ctrl` (0xBF39) when
`spawn_ctrl` (0xE12D) bit 0 is set (the encounter-counter mutators
`inc/dec_encounter_a` set this bit). Clears that bit, then indexes the
spawn lookup tables (`kb/data/spawn_table.md`) by scroll position and writes:
spawn-timer reload (0xE137/0xE138), spawn sub-table params (0xE135/0xE136),
and `spawn_table_ptr` (0xE133/0xE134 = `0xBECC + offset`).

## Analysis

```
BE27  RES 0,(IX+0x2D)            ; clear "recompute" request (E12D bit0)
BE2B  A = (IX+0x2E) + (IX+0x32)  ; position = spawn_pos_hi + 0xE132, clamp 0xFF
BE35  if A >= 0xA0: A = 0x9F     ; clamp to table range
BE3B  SRL A                      ; A = position >> 1   (A itself is halved)
BE3D  C = A                      ; timer index base, still >> 1
BE3E  DE = A & 0x7E              ; even index into 0xBE7C pair table,
                                 ;   i.e. (position >> 1) & 0x7E
BE43  HL = 0xBE7C + DE
      E = (HL); cmp (IX+0x35) with (HL+1); reset E135 if exceeded
BE53  C >>= 4                    ; position >> 5 → timer index
BE5C  (IX+0x36) = byte from 0xBE7C table
BE60  HL = 0xBE76 + C; B = (HL)  ; timer reload value
      (IX+0x37) = (IX+0x38) = B  ; spawn_timer + reload
BE6B  HL = 0xBECC + DE
      (IX+0x33/0x34) = HL        ; spawn_table_ptr -> entity list slice
BE75  RET
```

## Index correction (2026-07-30)

This sketch previously read `C = A >> 1` / `DE = A & 0x7E`, which made the pair
index look like it came from the *unhalved* position and put this entry in
conflict with [[spawn_table]]'s `(position >> 1) & 0x7E`. The raw instructions
settle it:

```
BE3B  CB 3F   SRL A        ; A = A >> 1 in place
BE3D  4F      LD C,A
BE3E  E6 7E   AND 0x7E
BE40  5F      LD E,A
```

`SRL A` rewrites `A`, so both `C` and `DE` derive from the halved value:
`DE = (position >> 1) & 0x7E` and `C = position >> 1`, which the later `C >>= 4`
turns into `position >> 5` for the timer index — the figure both files already
agreed on. [[spawn_table]] was right; the reordering in this sketch was the
error. It mattered: `DE` is reused at 0xBE6B as the offset into the 0xBECC
entity list, so a doubled index would spawn the wrong types everywhere.

## Tables

- `0xBE76` — 7 timer-reload values (descending; faster spawns later).
- `0xBE7C` — position→{offset,count} pairs.
- `0xBECC` — flat entity-type list.

See `kb/data/spawn_table.md` for full contents and
`kb/symbols/0x9000-scroll/ground_struct_spawn_ctrl.md` for the consumer.
