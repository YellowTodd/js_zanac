---
address: 0xE136
kind: data
name: spawn_subtable_max
confidence: confirmed
sprint: "0027"
tags: [spawn, gamestate, scroll]
---

# spawn_subtable_max

Upper bound for spawn_subtable_ctr (0xE135). Loaded from the paired table at
0xBE7C by `SUB_ram_be27` (0xBE27) at code 0xBE5D:

```z80
LD  A, (HL)           ; HL = 0xBE7C + scroll_index
LD  (IX+0x36), A      ; E136 = table entry
```

The table at 0xBE76 has paired entries (timer_reload, subtable_max):
`38 32 2C 22 1C 14 00 05 03 04 05 06 08 06 0B 05 ...`

When spawn_subtable_ctr reaches spawn_subtable_max, the sub-table index resets
to 0. This controls how many entries are read from one spawn sub-table before
advancing to the next.

Values observed:
- game_start / early: 0x05
- base_approach and beyond: 0x08 (denser spawn pattern)
