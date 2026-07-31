---
address: 0xE780
kind: data
name: attack_list
confidence: confirmed
sprint: "0031"
tags: [base, gamestate, entity]
---

# attack_list

## Summary

RAM array at 0xE780 storing the addresses of entity slots that form an active
ground base. Written by `place_tile_group` (0x95ED) during base-encounter
tile placement. Consumed by some routine (not yet identified) that reads the
entries using `base_attack_count` (0xE151/0xE152) as the count.

The list pointer at 0xE71E is maintained only by `place_tile_group` itself;
no other ROM code reads 0xE71E (confirmed by full-ROM byte search, sprint 0022).

## Entry format (4 bytes per entry)

| Byte | Content |
|------|---------|
| 0–1 | 16-bit LE entity slot address (the ground-structure entity for this base column) |
| 2–3 | Unknown (zero in observed captures; may be filled by a consumer) |

## Related addresses

| Address | Name | Role |
|---------|------|------|
| 0xE71E  | attack_list_ptr | 16-bit LE write pointer into this table; starts at 0xE780 |
| 0xE150  | base_encounter_flags | Bit 0: base active (set after list is fully written) |
| 0xE151  | base_attack_count | Entry count (incremented per entry, 0 at list start) |
| 0xE152  | base_attack_count_snap | Snapshot of 0xE151 taken at base finalisation |

## Known consumers

Both consumers share the helper `SUB_ram_909c` (0x909C) which reads the 16-bit
slot address from (HL), advances HL by 4, and returns with IY = slot address.

### 1. `SUB_ram_8f5e` (0x8F5E) — main attack sequencer

Called every frame from the main game loop (0x4074, 0x40AC). Manages the full
base-encounter state machine:
- Reads 0xE100+0x50 = 0xE150 (base_encounter_flags) to determine phase.
- When phase transitions to "attack" (bit 0 set, countdown expired):
  - Sets 0xE150 = 0x02 (bit 1 = attack phase active).
  - Iterates all `base_attack_count` (IX+0x51 = 0xE151) entries in 0xE780.
  - For each body entity slot (IY): writes a dispatch-callback pointer (16-bit
    LE address into the 0x93AB parameter table) to IY+0x0F/IY+0x10.
  - The dispatch table at 0x93AB cycles 8 entries (0x93BB–0x93E0), each a
    variable-length velocity-parameter list consumed by body entity handler
    0x8A5A via `SUB_ram_8bf5`.

### 2. `LAB_ram_934D` (0x934D) — body-alive health check

Called when 0xE150 bit 2 is set (attack phase 2). Iterates 0xE780 with
base_attack_count as the count; for each body entity IY, checks if
`IY+0x00 AND 0x7F` is in range 0xC9–0xCE (types 73–78 with bit 7 set =
alive running entities). Clears 0xE150 and ends the encounter when all
body slots are destroyed.

## Write sequence (0x9624–0x962F, inside place_tile_group)

```
EX DE, HL               ; HL ← entity context; DE ← tile ptr
PUSH HL
LD HL, (0xE71E)         ; HL = current write ptr
LD (HL), E / INC HL     ; write slot addr low
LD (HL), D / INC HL×3  ; write slot addr high; advance ptr by 4
LD (0xE71E), HL         ; update ptr
INC (0xE151)            ; increment count
```
