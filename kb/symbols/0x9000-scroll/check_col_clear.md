---
address: 0x9B22
end: 0x9B61
kind: routine
name: check_col_clear
confidence: confirmed
inputs:
  HL: "(ignored) — routine hardcodes HL = 0xE620"
outputs:
  CF: "set = column blocked by existing ground-structure entity; clear = ok to place"
  HL: "on the carry-clear path, the free entity slot found — this routine is also the allocator"
clobbers: [AF, BC, DE, HL]
calls: []
called_by: [0x95ED]
tags: [scroll, ground-structure, entity]
sprint: "0010"
---

# check_col_clear

## Summary

Scans the type bytes of entity slots 5–25 (at stride 32 starting from slot 25
backward to slot 5) to determine whether a ground-structure slot with a blocking
tile type is already present. Returns carry set if blocked, carry clear if a new
structure can be placed.

**Correction from sprint 0009:** 0xE620 is NOT a VRAM name-table shadow.
It is the start of entity slot 25 (0xE300 + 25×32 = 0xE620). The routine
scans slot type bytes at addresses 0xE620, 0xE600, 0xE5E0, …, 0xE3A0 —
exactly the byte-0 (type byte) of entity slots 25 down to 5.

## Analysis

Source lines 6881–6924. Key instructions:

```
9B22  LD HL, 0xE620          ; start at slot 25 type byte (hardcoded)
9B25  LD B, 0x15             ; 21 iterations (slots 25→5)
9B27  LD DE, 0xFFE0          ; stride = -32 (one slot back)
; Phase 1 — walk backward finding last non-zero type
9B2C  LD A, (HL)
9B2D  AND A
9B2E  JR Z, 9B61             ; if type = 0 (slot inactive), carry clear
9B30  ADD HL, DE             ; HL -= 32 (prev slot)
9B31  DJNZ 9B2C
; Phase 2 — walk forward checking for "compatible/passable" types
9B33  LD DE, 0x20            ; stride = +32
9B38  ADD HL, DE
9B39  LD A, (HL)
9B3A  AND 0x7F               ; mask flag bit 7
9B3C  CP 0x14                ; → carry clear (passable)
9B3E  CP 0x25                ; → carry clear
9B40  CP 0x26                ; → carry clear
9B42  DJNZ 9B38
; Phase 3 — walk backward checking for blocking types
9B4F  LD A, (HL)
9B51  AND 0x7F
9B53  CP 0x27                ; → SCF (blocked: single-column marker type)
9B55  CP 0x46; JR NC, 9B5D  ; → SCF if type >= 0x46 (wide structure types)
9B5D  SCF
9B61  RET
```

### Entity type interpretation used by this routine

| Type (masked & 0x7F) | check_col_clear verdict | Entity meaning |
|---|---|---|
| 0x00 | skip (inactive slot) | no entity |
| 0x01 (player) | no match → carry clear | player ship — ignored |
| 0x14 | carry CLEAR | passable ground tile type |
| 0x25, 0x26 | carry CLEAR | passable ground tile types |
| 0x27 | carry SET | blocking column-marker entity (type 39) |
| ≥ 0x46 (e.g. 0x52) | carry SET | wide/tall ground structure entity |

## Live debug verification (sprint 0010)

Snapshot with structures visible showed:

| Slot | Addr | raw type | masked | Verdict |
|---|---|---|---|---|
| 25 | 0xE620 | 0x00 | 0x00 | zero/skip |
| 24 | 0xE600 | 0xD2 | 0x52 | BLOCKED (≥0x46) |
| 23 | 0xE5E0 | 0xD2 | 0x52 | BLOCKED |
| 9  | 0xE420 | 0x27 | 0x27 | BLOCKED (==0x27) |
| 6  | 0xE3C0 | 0x27 | 0x27 | BLOCKED |
| 5  | 0xE3A0 | 0xAC | 0x2C | other |

## It is also the slot allocator (2026-07-30)

This entry described the routine purely as a predicate. It is equally the
**ground-structure slot allocator**: phase 1 walks slots 25 → 5 and bails out
the moment it finds an inactive one —

```
9B2C  LD A,(HL)
9B2D  AND A
9B2E  JR Z, 9B61        ; free slot found: return with carry clear AND HL on it
9B30  ADD HL, DE        ; else step back one slot
9B31  DJNZ 9B2C
```

— so the carry-clear return leaves `HL` pointing at that free slot. Its only
caller, [[place_tile_group]] (0x95ED), relies on exactly that: after
`CALL 0x9B22` it writes the new structure's type/Y/X straight through `HL`
(0x963A–0x964E). Treating the routine as a pure "is the column blocked?" test
leaves the placement code with no destination.

Note the consequence for the two exit paths: carry clear means *both* "not
blocked" and "here is where to put it", while the blocked path (phases 2–3) runs
only when no free slot exists at all.

## Notes

- The scan addresses (0xE620, 0xE600, …, 0xE3A0) coincide exactly with the
  type-byte (byte 0) of entity slots 25 down to 5, since each slot is 32 bytes.
- Entity slots 0–4 are reserved for player ship and player-controlled entities
  (shots and fire projectiles); they are below the scan range
  (0xE3A0 = slot 5 is the lowest address reached).
- bit 7 of the type byte is a state flag and is stripped with `AND 0x7F`
  before the comparisons — the dispatch trick in entity_dispatch (ADD A,A
  overflow) achieves the same masking effect automatically.
