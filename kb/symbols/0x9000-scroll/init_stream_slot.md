---
address: 0x95C0
end: 0x95EC
kind: routine
name: init_stream_slot
confidence: confirmed
inputs:
  IY: "pointer to 4-byte stream slot in 0xE2E0 table"
  HL: "pointer into ROM level-data descriptor"
  C: "tile-Y base offset"
  E: "raw slot-config byte (bit 3 = timer flag)"
outputs:
  HL: "advanced past consumed descriptor bytes"
  DE: "tile-data stream pointer (also stored in IY+2:3)"
clobbers: [AF]
calls: [0x95ED]
called_by: [0x95A8]
tags: [scroll, level-map, ground-structure]
sprint: "0067"
---

<!-- Confirmed sprint 0067: this is the per-record helper of map-script cmd 5
(and cmd B); its 3-or-4-byte consumption (by config bit3) is exactly what makes
sprint 0062's grammar walk all 9 scripts desync-free. See
[[ground_structure_placement]], [[load_stream_slots]], [[place_tile_group]]. -->


# init_stream_slot

## Summary
Configures one 4-byte stream slot in the 0xE2E0 inner-stream table, given a
ROM level-data descriptor. Helper called for each slot by `load_stream_slots`.

## Analysis
Source lines 6268–6294.

### Slot layout (4 bytes at IY)
| Offset | Field | Meaning |
|--------|-------|---------|
| IY+0 | status | tile-Y + C offset; bit 6 = timed flag |
| IY+1 | timer/data | frame-countdown (timed) or tile data byte |
| IY+2 | ptr_lo | low byte of ROM tile-data pointer |
| IY+3 | ptr_hi | high byte of ROM tile-data pointer |

### Execution
1. `IY+0 = (HL++) + C` — row position (tile-Y from descriptor + base offset C).
2. **Timer path** (`BIT 0x3, E` set): `SET 0x6, (IY+0)` marks the slot as
   timed; `IY+1 = (HL++)` stores the frame-countdown byte.
3. `HL++` (skip one byte, past optional timer byte).
4. `DE = (HL++) | (HL++ << 8)` — read 16-bit ROM tile-data pointer.
5. **Non-timed path** (bit 6 of IY+0 clear):  
   Read first tile `A = (DE++)`. If `A == 0` (stream-segment boundary),
   `CALL 0x95ED` (`place_tile_group`) to advance DE past the segment header.
   Store result in `IY+1`.
6. `IY+2 = E; IY+3 = D` — store updated stream pointer.
