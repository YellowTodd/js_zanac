---
id: "0030"
status: done
range: 0x4560-0x4648
strategy: pattern_matching
budget_turns: 18
---

# Sprint 0030 — Collision detection system

## Goal

The collision routines at 0x4560–0x4648 are inside a Ghidra-rendered DB block
(mixed with credits text, confirmed by sprint 0021 analysis). The sprint 0021
decode partially traced the first ~30 bytes (storing entity type into IX+0x18
as a collision class cache). This sprint completes the decode:

1. **Collision class table at 0x716B** — maps entity type (0–89) to class (0–7).
   Read from ROM and build the full type→class table.
2. **Full 0x4560 routine decode** — reads both entity types (IX and IY), looks
   up their collision classes, checks the collision matrix, then computes
   hitbox overlap using the size table at 0x45C9.
3. **Collision matrix** — which class pairs deal damage to which? (e.g. player
   shot vs. ground structure? Enemy projectile vs. player during invincibility?)
4. **Live verification** — arm entity_post with a conditional breakpoint on
   0x4560, confirm which entity pair triggers a collision event.

## Inputs

- `kb/data/entity_table.md` (sprint 0021) — +0x18 confirmed as collision type
  cache: stores entity's own type (bits 0–6) when entity_post runs 0x4560
- `kb/symbols/0x4000-init/entity_post.md` — calls 0x4560 with IX=enemy, IY=player
- `kb/symbols/0x4000-init/collision_size_table.md` — at 0x45C9, confirmed (size)
- Sprint 0021 partial decode of 0x4560:
  ```
  4560: DD 7E 00  LD A,(IX+0)     ; entity type
        E6 7F     AND 0x7F         ; strip bit7
        DD 77 18  LD (IX+0x18),A   ; cache in +0x18
        5F        LD E,A
        16 00     LD D,0
        21 6B 71  LD HL,0x716B    ; collision class table
        19        ADD HL,DE        ; HL → table[entity_type]
        7E        LD A,(HL)        ; A = collision class (0-7)
  ```
  Then reads IY's type similarly, and proceeds to matrix check.

## Verification plan

### Step 1 — Read and decode the full 0x4560 routine from ROM

The routine starts at 0x4560. From sprint 0021 we know it's in a DB section.
Read 150 bytes from 0x4560 and decode manually, following the established
pattern from sprint 0021 (entity_update was decoded the same way).

```python
data = bytes(msx.read_memory(0x4560, 150))
# print hex rows for manual Z80 decode
for i in range(0, 150, 16):
    chunk = data[i:i+16]
    print(f"  {0x4560+i:04X}: {' '.join(f'{b:02X}' for b in chunk)}")
```

### Step 2 — Read the collision class table (0x716B)

```python
# Table is indexed by entity type (0–89) → 90 bytes
class_table = bytes(msx.read_memory(0x716B, 90))
print("Collision class table (type → class):")
for typ in range(90):
    cls = class_table[typ]
    if cls > 0:   # only non-zero entries
        print(f"  type {typ:2d} (0x{typ:02X}) → class {cls}")
```

Expected: player (type 1) → class A; player shots (type 2) → class B;
enemy projectiles (type 35, 37) → class C; ground structures (types 39, 44, 70+)
→ class D; fire weapons (type 3) → class E; etc.

### Step 3 — Find and read the collision matrix

After the class lookup, the routine must check if class(IX) and class(IY)
interact. Look for a matrix table (likely a bitmask or 8×8 byte table) in the
decoded bytes. Read and print.

### Step 4 — Live verification

```python
# Arm a conditional BP at entity_post (0x44BA) that breaks only when
# a collision fires (entity_clear is called via JP 0x453E)
msx.cmd("set ::collision_fired 0")
wp = msx.set_breakpoint(0x453E, "set ::collision_fired 1; debug break")
# Play normally; when bp fires, dump IX, IY and their types
```

## Focus questions

- Do player shots (type 2) collide with ground structures (type 44)? The game
  description says "all-range cannon destroys ground objects" — confirm via matrix.
- Does the player (type 1) with invincibility flag (+0x05 bit7) bypass collision?
  Or is invincibility handled entirely by the color change (entity_post still runs)?
- Do enemy projectiles (type 35) collide with each other, or only with the player?
- What does class 0 mean — "no collision at all"?

## Expected output

- New `kb/symbols/0x4000-init/collision_routine.md` — full decode of 0x4560
- Collision class table documented in `kb/data/entity_jump_table.md` (new column)
  or a new `kb/data/collision_classes.md`
- Collision matrix (which class pairs deal damage) documented

## Summary (filled at end)

### What we found

**Collision check is two routines, not one.**

The sprint assumed 0x4560 was a single "collision dispatch" routine that looked
up entity types, found collision classes, and checked a matrix. The actual ROM
is different:

- **0x45A0–0x45C8 `hitbox_setup_ix`** — called first; computes IX entity's
  hitbox bounds (Y: BC, X: shadow BC') from its sat_name and the size table.
- **0x4560–0x459F `hitbox_check_iy`** — checks IY entity's sprite against
  those bounds; returns carry if overlap detected.

There is no collision class lookup in either routine. The `LD HL,0x716B`
that sprint 0021 attributed to 0x4560 was a misread; the actual instruction
is `LD HL,0x45C9` (the size table).

**Size table at 0x45C9 encodes Y and X half-sizes as consecutive byte pairs.**

Sprint 0018 documented a single "radius" per sprite. The full decode reveals
the routine reads two bytes per entity: `table[sat_name >> 1]` = Y half-size,
`table[(sat_name >> 1) + 1]` = X half-size. The table is updated.

**0x716B is not a collision class table.**

The 90 bytes at 0x716B appear to be unrelated data (immediately after the
entity_jump_table at 0x70B7, which spans 90 × 2 = 180 bytes ending at 0x716A).
The "collision class" abstraction described in the sprint does not exist in the
decoded range. Class-based dispatch, if present, would be inside 0x44D4 (still
undecoded) — a candidate for a future sprint.

**Live verification confirmed.**

Breakpoint at 0x453E fired during gameplay with IX=0xE420 (type 44, ground
structure) and IY=0xE340 (type 2, player shot). Confirms that entity_post
checks player shots against ground structures each frame via this pair of
routines.

### Sprint 0021 correction

The partial decode `LD HL,0x716B ; collision class table` was wrong. ROM bytes
at 0x4567–0x456B are `16 00 21 C9 45` = `LD D,0 / LD HL,0x45C9`.

### Outstanding questions (future sprint)

- What is inside `0x44D4`? It sets IY (player-side entity selector) and calls
  0x4560. The class-lookup logic, if any, lives there.
- Does invincibility (`+0x05 bit 7`) suppress the 0x4560 call inside 0x44D4,
  or is it handled differently?
- What is at 0x716B? Probably not collision-related; may be entity name tiles
  or a secondary lookup table.
