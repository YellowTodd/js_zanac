---
address: 0x95ED
end: 0x9674
kind: routine
name: place_tile_group
confidence: confirmed
inputs:
  DE: "ROM tile-data stream pointer; (DE) was just read as 0 (segment boundary)"
  IY: "active stream slot (0xE2E0 table entry)"
  IX: "entity slot base (entity table, 0xE300+)"
  HL: "(not an input) — set per record by check_col_clear to the free entity slot"
outputs:
  DE: "advanced past the consumed tile-group descriptor"
  AF: "preserved (restored from stack on return)"
clobbers: [BC, HL, IY]
calls: [0x9B22]
called_by: [0x95C0, 0x9888]
tags: [scroll, level-map, ground-structure, base-encounter]
sprint: "0067"
---

# place_tile_group

## Summary
Reads the next tile-group descriptor from the ROM level-data stream and places
ground-structure tiles into the name-table placement buffer. Called when a
stream pointer reaches a 0-byte (end-of-segment marker), to advance to the
next group of tiles for the current column.

Two entry points share the same body:
- **0x95ED**: reads one extra byte from (DE) before entering the shared body.
  Used when the 0-byte has not yet been consumed.
- **0x95EF**: enters with the byte-after-zero already consumed by the caller.

## Analysis
Source lines 6295–6385 (sub_95ED / sub_95EF body).

### Control byte C (= byte at (DE) / the byte after the 0-marker)
| Bit | Meaning |
|-----|---------|
| 7 | Base encounter: this tile group is a ground base |
| 6 | Double-width ground structure |
| 5 | Triple-width extension |
| 4-0 | Column count B (number of tile-placement records) |

### Execution

1. `A = (DE++)` — read control byte C; `B = A AND 0x1F` (count of records).
2. **Base flag** (`BIT 0x7, C` set): `HL = 0xE780; (0xE71E) = HL` — sets
   base-attack list write pointer to 0xE780. `(0xE151) = 0` — resets count.
3. **Main loop** (`LAB_9606`, B iterations):
   - `CALL 0x9B22` (`check_col_clear`) — test name-table column for conflicts.
   - **Carry set (blocked):** skip 3 bytes in DE (`INC DE × 3`); optionally
     increment `IX+0x1D` for wide structures (bits 5/6 of C).
   - **Carry clear (ok):** `HL` now points at the free entity slot
     `check_col_clear` found; write the record's 3 bytes there as
     **type, Y, X** — the third stream byte is not stored raw but folded into
     the X coordinate as `IY+0 × 8 + DE_byte − 0x20` (0x9645). For wide
     structures, also store `IX+0x1D` and increment it.
4. **Base finalisation** (after loop, if bit 7 C): `(0xE152) = (0xE151)` —
   copy count; `(0xE150) = 1` — signal an active base encounter.
5. `POP AF / RET` — A is restored to the value it had on sub entry.

## Record layout and byte consumption (2026-07-30)

Stated explicitly, because a stream that mis-counts here desynchronises the
*greeble* stream rather than the map script, which the script-walk check cannot
catch:

```
entry 0x95ED:  [timer] [control C] [rec 0] [rec 1] ... [rec N-1]
                                   \___ 3 bytes each, N = C AND 0x1F ___/

total consumed = 2 + 3 × (C AND 0x1F)
```

The `[timer]` byte is the one read at 0x95ED; it is pushed at 0x95EF and
restored by `POP AF` at 0x9676, which is why callers use the returned `A` as the
stream slot's reload timer (`LD (IY+1),A` at 0x9A19 / 0x95E3).

Every record costs exactly 3 bytes on **both** paths — placed at 0x963A–0x9643,
or skipped by the three `INC DE`s at 0x960C — so the advance is independent of
whether the column was clear.

Each record is `[type][y][xCell]`, written into the entity slot as byte 0
(type), byte 1 (Y) and byte 2 (X, via the `×8 − 0x20` fold above). The `0x20`
undoes the sprite attribute table's early-clock bias, matching the `0x8F`
colour byte the player and structure sprites carry.

## Key data addresses
| Address | Role |
|---------|------|
| 0xE71E  | Base-attack list write pointer (16-bit LE); only accessed by this routine |
| 0xE780  | Base-attack list entries (4 bytes each; confirmed sprint 0022) |
| 0xE150  | Base-encounter active flag (set to 1 when base group placed) |
| 0xE151  | Running count of base-attack entries written |
| 0xE152  | Final count of base-attack entries (copied from 0xE151 after loop) |
| IX+0x1D | Per-entity slot field incremented for multi-column structures |

## Attack-list entry format (confirmed sprint 0022)

The code at 0x9624–0x962F writes one 4-byte entry per placed entity slot:

```
9624  EX DE, HL            ; HL ↔ DE (old HL = entity context pointer)
9625  PUSH HL              ; save old DE (tile-stream pointer)
9626  LD HL, (0xE71E)      ; HL = current attack-list write ptr (starts at 0xE780)
9629  LD (HL), E           ; write low byte of entity slot address
962A  INC HL
962B  LD (HL), D           ; write high byte of entity slot address
962C  INC HL × 3           ; advance ptr by 4 total
962F  LD (0xE71E), HL      ; update pointer
9632  INC (0xE151)         ; increment entry count
```

Each entry = **4 bytes** at 0xE780+N×4:
- Bytes 0–1: 16-bit LE entity-slot address (the ground-structure entity placed for this base column)
- Bytes 2–3: purpose unknown (not written here — may be filled by another routine or left as zeros)

**0xE71E is ONLY accessed by this routine** (confirmed by full-ROM byte search). No entity handler reads 0xE71E. Whatever consumes the attack list at 0xE780 uses 0xE151/0xE152 (count) and reads 0xE780+ directly.

## Confirmation (sprint 0067)

Upgraded `hypothesis` → `confirmed`. Two independent lines:
- **Byte-exact record consumption** matches sprint 0062's map-script grammar
  (this routine is the segment-boundary helper of cmd 5 / the `0x9888` scroll
  reader); the grammar walks all 9 scripts desync-free.
- **Base-encounter outputs live-observed (sprint 0065).** In a round-1 base
  fight the base finalisation here sets `0xE150=1` (active) and copies the
  attacker count into `0xE152`; the live capture read `E150` bit1 set with the
  base active and watched `E152` decrement to 0 as segments died, driving the
  base-clear award ([[base_clear_award_index_table]]) and `base_attack_spawn`
  reading its patterns ([[base_attack_patterns]]). The `0xE780` attack list this
  routine fills is exactly what `base_attack_spawn` (0x8FDE) walks.
