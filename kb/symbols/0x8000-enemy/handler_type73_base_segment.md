---
address: 0x8a5a
end: 0x8bc9
kind: routine
name: handler_type73_base_segment
confidence: confirmed
inputs:  { IX: "entity slot" }
outputs: {}
clobbers: [AF, BC, DE, HL, IY]
calls:   [0x8948, 0x8bf5, 0x8c15, 0x8d14, 0x44ca, 0x7904, 0x5189, 0x8ca2, 0x8bc1]
called_by: [0x445f]
tags: [entity, enemy, base, segment]
sprint: "0052"
---

# handler_type73_base_segment

Shared handler for **types 73–79** — the destructible **base segments** (the
ring of parts around a base core). Init is **gated**: it only activates once the
scroll flag (0xe700 bit 1) and the base-active flag (0xe150 bit 1) are both set;
until then it scrolls down with the map. Each type reads its parameters
(sprite, HP, position offsets, motion) from [[base_segment_table]] (0x8df1) by
`(type − 0xc9) × 5`, and records its VRAM address in the 0xe782 segment table.
Was a raw DB block (0x8a5a–0x8bc9); disassembled sprint 0052, ROM byte-identical.

```
8a5a  BIT 7,(IX+0x00) / JP NZ,0x8ae8        ; active → run
8a61  LD A,(0xe700) / BIT 1,A / JR Z,..      ; not scrolled in → scroll Y +8 and wait
8a70  LD A,(0xe150) / BIT 1,A / RET Z         ; base not active yet → wait
8a76  SET 7 / Y += 0x10 / +0x05=0 +0x0c=0 +0x0d=1
8a8f  compute VRAM addr (0x8948) → +0x06/07; store to 0xe782 + (+0x1c)*4
8aad  idx = (type − 0xc9)*5 ; HL = base_segment_table(0x8df1)+idx
8abe  +0x03 = sprite ; +0x19 = HP ; +0x01/+0x02 += y/x offsets ; +0x15 = motion
; active (0x8ae8): animates, moves via +0x0f/10 cursor (0x8bf5), runs hit-sub
8b76  CALL 0x7904 ; on destroy: branch on +0x19 / +0x18, spawn child (0x8bca),
                  ; decrement encounter, on last segment open the base
```

## Full decode (2026-07-30, for the web port)

**0x8AEF tests the entity type, not the animation phase.** `CP 0xCF / JP Z,
0x8B6C` sends **type 79 — the core** straight to the firing accumulator; it has
no shutter animation. Every other type runs the animation first.

### The shutter (0x8AFF)

`+0x0C` is a 0..3 phase and `+0x0D` its step (±1). Each frame the rate for the
current phase is added to `+0x0E`; on carry the phase moves by the step:

| phase | rate field | meaning |
|-------|-----------|---------|
| 0 | +0x09 | shut - **0x8B67 returns before `entity_post`, so a shut segment cannot be hit at all** |
| 1, 2 | +0x0A | opening / closing |
| 3 | +0x0B | wide open - the only phase that fires (0x8B68) |

Reaching 0 loads the next pattern record and reverses the step; reaching 3 just
reverses it. Both, and every ordinary step, repaint through 0x8B60.

The three rates come from a 3-byte record in the segment's **attack pattern**
([[base_attack_patterns]], assigned by [[base_tick]] at 0x8FDE);
`base_pattern_load_record` (0x8BF5) advances the cursor +0x11/+0x12 and rewinds
to the pattern base +0x0F/+0x10 on the `0x00` terminator.

### Drawing (0x8C15)

A 7-entry jump table at **0x8C1D** (currently mis-decoded as instructions).
All non-core types share the blitter at 0x8C2D, differing only in the first
tile, row count, column count and whether the tile index advances:

| type | first tile | rows | cols | step |
|------|-----------|------|------|------|
| 73 | 0xD3 + 4·phase | 2 | 2 | 1 |
| 74 | 0xC3 + 4·phase | 2 | 2 | 1 |
| 75 | 0xBF + phase | 1 | 1 | 0 |
| 76 | 0xBF + phase | 1 | 2 | 0 |
| 77 | 0xBF + phase | 2 | 1 | 0 |
| 78 | 0xBF + phase | 2 | 2 | 0 |
| 79 | 3×3 block by HP: ≥0x15 → 0x8CED, >0 → 0x8CFA, 0 → 0x8D07 | | | |

(`RRC D` at 0x8C4A is a *rotate*, so `D=1` never reaches zero — the column
count is simply "2 if D≠0".)

### Firing (0x8D14)

A second 7-entry jump table at **0x8D1C**. Projectile types are 0x15 (21),
0x2A (42), 0x2B (43) and 0x2D (45); the direction code goes in the child's
+0x1A, and `spawn_child_at_parent` (0x8DDB) writes **only** +0x00/+0x01/+0x02/
+0x1A — the rest of the slot keeps whatever the previous occupant left.

- **73**: +0x13 steps by 3; nibble 0-8 → type 0x15 in that direction, 0x0E/0x0F → type 0x2A, 9-0x0D loops
- **74 / 77**: a burst of 4 / 2 consecutive directions, wrapping 0..8
- **75**: one type 0x2A
- **76**: +0x13 counts down; direction `c = +0x13 & 7`, and unless `c == 4` a mirrored second shot at `8 - c`
- **78**: `player_pos_snapshot` then a **five-way fan** at deltas 0, −1, +1, −2, +2 (table 0x8DB3)
- **79** (core): every 4th call the plain 0x2A, otherwise type 0x2D with a random direction `R & 0x0C`

### Dying

Ordinary segments: `base_segment_draw_wreck` (0x8CA2) stamps a rubble block
chosen by the shape id in **+0x18** (0x4B → 0x8CE1, 0x4C → 0x8CE4, 0x4D →
0x8CE8, else 0x8CDA), the slot becomes type 0x50, and **(0xE152) is
decremented** at 0x8BB1 — that is what eventually clears the base. The core
(+0x18 == 0x4F) instead sets +0x05 bit 1 and burns down a 0x20-frame counter
(0x8BB6), repainting every 4th frame.

## Related

[[base_tick]] (0x8f5e, the driver), [[base_segment_table]] (0x8df1),
[[base_attack_patterns]] (0x93ab), [[handler_type72_base_core]] (the warp orb,
*not* part of a base despite the name), `data_e150` (base-active gate),
[[entity_jump_table]] (73–79).
