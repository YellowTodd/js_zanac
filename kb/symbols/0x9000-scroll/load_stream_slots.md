---
address: 0x95A8
end: 0x95BF
kind: routine
name: load_stream_slots
confidence: confirmed
inputs:
  HL: "pointer to column-group slot descriptor in ROM level data"
  C: "tile-Y base offset (row) for this column group"
outputs:
  HL: "advanced past the consumed descriptor bytes"
  IY: "last IY slot address written (0xE2E0 + index×4)"
clobbers: [AF, BC, DE, IY]
calls: [0x95C0]
called_by: [0x9888, 0x95A0]
tags: [scroll, level-map, ground-structure]
sprint: "0067"
---

# load_stream_slots

## Summary
Reads a column-group slot descriptor from HL and activates N tile-stream slots
in the 0xE2E0 table (8-entry × 4-byte inner stream table). Called when a new
group of ground-structure tile columns enters the active scroll window.

## Analysis
Source lines 6251–6267.

Entry reads `B = (HL++)` as the count of slots to configure. The inner loop
(`LAB_95AA`, B times):

1. `A = (HL)` — slot-config byte.  
   - Bits 3-0 (after `RES 0x3, A`): stream-slot index (0–7 after bit-3 cleared).  
   - Bit 3 (in original `E`): timer-slot flag, forwarded to `init_stream_slot`.
2. `ADD A, A; ADD A, A` — multiply index by 4 (byte offset within 0xE2E0 table).
3. `IY = 0xE2E0 + index×4` — address of the target stream slot.
4. `E = (HL++)`  — re-reads the raw byte (with timer flag) as argument to sub.
5. `CALL 0x95C0` (`init_stream_slot`) — writes the 4-byte slot.
6. `DJNZ LAB_95AA`.

After the loop, `RET` with Z flag from last `init_stream_slot` call.

## Key data addresses
| Address | Role |
|---------|------|
| 0xE2E0  | 8-entry × 4-byte inner stream slot table |

## Confirmation (sprint 0067)

This is the body of **map-script command 5** (`0x95A0` → `CALL 0x95A8`; see
[[ground_structure_placement]]). Sprint 0062's byte-exact grammar walks all 9
scripts + the warp stub **desync-free** using exactly this routine's per-record
consumption (each record 4 or 5 bytes by config bit3), which is only possible if
the decode here is correct — a strong static confirmation. Upgraded
`hypothesis` → `confirmed`. See [[init_stream_slot]] (the per-record helper) and
[[level_script_format]].
