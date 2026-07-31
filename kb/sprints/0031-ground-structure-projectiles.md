---
id: "0031"
status: done
range: 0x8094-0x81A0
strategy: live_debug
budget_turns: 12
---

# Sprint 0031 — Ground-structure projectiles (types 46–55)

## Goal

Types 46–55 share a single dispatch handler at 0x8094 with an internal subtable
at 0x8189 (one entry per type, 10 types). From `entity_jump_table.md`: these are
"ground-structure projectiles (10 types, subtable at 0x8189 indexed by type-46)".
They are spawned by ground bases and represent the shots fired at the player
during a base encounter.

This sprint:
1. Decodes the subtable at 0x8189 (format: entity type + init params).
2. Classifies each of the 10 projectile types by sprite pattern and trajectory.
3. Confirms whether these are triggered by base encounter state (0xE150) or by
   a specific entity in the entity table.

**Dependency:** Sprint 0022 confirmed that `place_tile_group` sets up the attack
list at 0xE780 (entity slot addresses of base-body segments). The consumer of
that list, which spawns types 46–55, is likely what this sprint will identify.

## Inputs

- `kb/data/entity_jump_table.md` — types 46–55: handler 0x8094, subtable 0x8189
- `kb/symbols/0x9000-scroll/attack_list.md` (sprint 0022) — attack list at
  0xE780; consumer not yet identified; potentially the spawner of types 46–55
- `kb/symbols/0x9000-scroll/base_encounter_ctrl.md` — 0xE150 (base active flag)
- Sprint 0022 caller map: `CALL 0xBFAB` at 0x8F58 — an enemy handler (address
  range 0x8F58 is near the types-73–79 "base-gated" handlers)

## Verification plan

### Step 1 — ROM decode of handler 0x8094 and subtable 0x8189

```python
# Handler entry
handler = bytes(msx.read_memory(0x8094, 0x60))
print("Handler 0x8094:")
for i in range(0, 0x60, 16):
    print(f"  {0x8094+i:04X}: {' '.join(f'{b:02X}' for b in handler[i:i+16])}")

# Subtable at 0x8189 (10 entries, unknown size)
subtable = bytes(msx.read_memory(0x8189, 40))
print("\nSubtable 0x8189:")
for i in range(0, 40, 8):
    print(f"  {0x8189+i:04X}: {' '.join(f'{b:02X}' for b in subtable[i:i+8])}")
```

### Step 2 — Synthetic base trigger (from sprint 0022 technique)

```python
with ZanacGame.launch() as game:
    game.wait_for_title(); game.start_game()
    msx = game.client
    time.sleep(2.0)

    # Set base-encounter state
    msx.write_memory(0xE71E, bytes([0x80, 0xE7]))  # pointer → 0xE780
    # Populate attack list with slot addresses from the active ground structures
    raw = bytes(msx.read_memory(0xE300, 26*32))
    entries = []
    for i in range(5, 26):
        typ = raw[i*32] & 0x7F
        if typ in (44, 70, 71, 81, 82, 87, 88, 89):
            addr = 0xE300 + i*32
            entries += [addr & 0xFF, addr >> 8, 0x00, 0x00]
    if entries:
        msx.write_memory(0xE780, bytes(entries))
        msx.write_byte(0xE151, len(entries)//4)
        msx.write_byte(0xE152, len(entries)//4)
    msx.write_byte(0xE150, 0x01)

    # Watch entity slots for types 46-55
    msx.cmd("set ::n 0")
    bp = msx.set_breakpoint(0x445F, "incr ::n; if {$::n % 5 == 0} {debug break}")

    for sample in range(20):
        msx.cont(); time.sleep(0.3)
        raw = bytes(msx.read_memory(0xE300, 26*32))
        for i in range(26):
            typ = raw[i*32] & 0x7F
            if 46 <= typ <= 55:
                slot = raw[i*32:(i+1)*32]
                y, x, sat = slot[1], slot[2], slot[3]
                print(f"  sample {sample} slot {i}: type={typ} Y={y} X={x} sat={sat:02X}")
    msx.remove_breakpoint(bp)
```

### Step 3 — Identify the attack-list consumer

From sprint 0022, no entity handler reads 0xE71E. Search for code that reads
0xE780 or 0xE152 directly:

```python
# Search ROM for LD A,(0xE152) = 3A 52 E1
search_rom_for_bytes(msx, bytes([0x3A, 0x52, 0xE1]), "LD A,(0xE152)")
# Search for LD HL,0xE780 = 21 80 E7
search_rom_for_bytes(msx, bytes([0x21, 0x80, 0xE7]), "LD HL,0xE780")
# Search for LD DE,0xE780
search_rom_for_bytes(msx, bytes([0x11, 0x80, 0xE7]), "LD DE,0xE780")
```

## Focus questions

- What is the subtable entry format at 0x8189? (Hypothesis: 3 bytes = sat_name,
  velocity, color — matching the pattern used in the shot param table at 0x778F)
- Which code reads 0xE780 / 0xE152 to consume the attack list?
- Are types 46–55 spawned by a ground-structure entity handler, by a scroll
  engine callback, or by the VBLANK ISR?
- What trajectory do types 46–55 follow? (Hypothesis: diagonal at various angles,
  matching the pattern of bullet types in the NES version)

## Expected output

- Updated `kb/data/entity_jump_table.md`: types 46–55 upgraded from hypothesis
  to confirmed with sprite/trajectory data
- New `kb/symbols/0x8000-enemy/handler_type46_ground_projectiles.md`
- `kb/symbols/0x9000-scroll/attack_list.md` updated: consumer identified

## Summary (filled at end)

### ROM-only decode (Steps 1 + 3 completed without openMSX)

**Subtable at 0x8189** — 5 entries × 4 bytes (not 10×2 as hypothesised).
Pairs of types share one entry; the odd/even bit is discarded by `AND 0xFE`
before doubling for the table offset. Field layout (confirmed from ROM bytes):

| Offset | Types  | flags | color | period | spawn_type        |
|--------|--------|-------|-------|--------|-------------------|
| 0      | 46/47  | 0x00  | 0x8F  | 32     | 0x26 → type 38 (burst_frag) |
| 4      | 48/49  | 0x40  | 0x8D  | —      | 0x15 → type 21 (light_bar)  |
| 8      | 50/51  | 0x20  | 0x8A  | 80     | 0x26 → type 38 (burst_frag) |
| 12     | 52/53  | 0x00  | 0x89  | 32     | 0x15 → type 21 (light_bar)  |
| 16     | 54/55  | 0x20  | 0x87  | 46     | 0x15 → type 21 (light_bar)  |

Flags byte bits: 5 = oscillating sweep (angle 12→4, motion pauses), 6 = Y-tracking.

**Handler 0x8094** fully traced:
- Init: X randomised by R register (0x30 left / 0xC0 right); vy=1+80/256≈1.3,
  SAT_NAME=0x48 (plane), bflags=0x01.
- Running—tracking (bit 6): compares (0xE301)=player Y; fires when Y crosses.
- Running—countdown (bit 6 clear): periodic fire; oscillating types sweep angle
  12→4→12, pausing motion during the burst.
- Fire subroutine `0x816D`: spawns child entity (type from +0x1F, angle from
  +0x1D) via `find_free_slot` + `0x8DDB`; also toggles parent body sprite
  between 0x50 (ready) and 0x54 (firing) via pointer at +0x1B/+0x1C.

**Attack list consumers** — ROM byte search for `LD HL, 0xE780`:
- `SUB_ram_8f5e` (0x8F5E): main attack sequencer; called every frame from main
  game loop (0x4074, 0x40AC); reads 0xE780 via `SUB_ram_909c` (0x909C); writes
  dispatch-callback pointers (into param table at 0x93AB) to body entity slots
  IY+0x0F/+0x10; sets 0xE150 = 0x02 on attack-phase transition.
- `LAB_ram_934D` (0x934D): body health monitor; iterates 0xE780 checking if
  types 73–78 (with bit 7) are still alive; ends encounter when all destroyed.
- 0x95FC: inside `place_tile_group` — writes the list (already known, sprint 0022).

**Trigger question**: types 46–55 are triggered indirectly through 0xE150:
`place_tile_group` sets E150 bit 0; `SUB_ram_8f5e` (every frame) runs the
state machine and eventually sets E150 bit 1 plus dispatch callbacks in body
entity slots; the body entity handler (0x8A5A, types 73–79) reads the dispatch
callback via 0x8BF5 to update its velocity. The exact call site that SPAWNS
types 46–55 was not isolated (the type-73-79 handler spawns type 35 "enemy
projectile" at 0x8BCF; a separate path spawns the gun entities, possibly via
a type-field mutation using IX+0x18 — remains hypothesis).

### Outputs
- New: `kb/symbols/0x8000-enemy/handler_type46_ground_projectiles.md`
- Updated: `kb/data/entity_jump_table.md` (types 46–55 row, handler grouping)
- Updated: `kb/symbols/0x9000-scroll/attack_list.md` (consumers identified, confidence → confirmed)
