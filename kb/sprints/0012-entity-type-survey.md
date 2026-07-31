---
id: "0012"
status: done
range: 0x70B7-0x70FF
strategy: data_table
budget_turns: 30
---

# Sprint 0012 — Entity jump-table survey

## Goal

Read the entity dispatch jump table at 0x70B7, map every type ID to its handler
address, and stub-decode each handler — especially ground-structure types (39, 44,
82) and any others active in sprint 0010 live dumps.

## Inputs

- `kb/data/entity_table.md` — type byte semantics, confirmed types 1/39/44/82
- `kb/symbols/0x4000-init/entity_dispatch.md` — jump table at 0x70B7, stride 2
- `source/zanac.asm` — jump table data lines and handler entry-point lines

## Verification plan

Static only: read jump table entries, follow each address into source, read
first ~20 instructions of each handler to characterise its role.

## Summary (filled at end)

Full entity jump table read directly from openMSX memory (0x70B7, 200 bytes).
Table covers types 0–89; types 90+ point into BIOS addresses (invalid).

**New confirmed identities:**
- **Type 11** (`handler_type11_base_spawner` at 0x7AD4): reads base health counter
  0xE130, selects Y/X from table at 0x7AF7, changes own type to 69 (running
  projectile), jumps to 0x7A67. This is the long-sought base projectile spawner.
- **Type 35** (`handler_type35_base_eye` at 0x8446): drives the base "animated eye"
  by accumulating 16/frame at 0xE12F and calling `base_encounter_ctrl` on overflow.
- **Type 39** (`handler_type39_col_marker` at 0x8525): countdown timer at +0x18,
  calls `entity_clear` (0x48D0) on expiry. Confirmed purely invisible marker.
- **Type 44** (`handler_type44_ground_struct` at 0x82D0): init calls `spawn_col_marker`
  (0x71DA) which writes type 0x27 to a new slot and links it via +0x1B/1C.
- **Type 69**: running base projectile (spawned by type 11).
- **Type 80** (`handler_type80_base_damage` at 0x8E14): decrements base health via
  `base_encounter_ctrl` 0xBFB3 on first call, then spawns explosion type 18.
- **Types 70–71, 81–82, 87–89** (handler 0x87AB): wide ground structures; init
  gated on scroll_flags bit 1; reads 0xE720 pointer for column displacement table.
- **Types 46–55** (handler 0x8094, 10 types): subtable at 0x8189 indexed by type-46;
  likely ground-structure bullet family.
- **Types 73–79** (handler 0x8A5A, 7 types): init blocked by 0xE150 bit 1; base-gated.

**New helper routines:**
- `entity_clear` (0x48D0): PUSH IX/POP HL + LDIR zero-fill, despawns slot.
- `spawn_col_marker` (0x71DA): allocates type-39 slot, links via parent +0x1B/1C.
- `entity_update` (0x4898): dispatches IX+0x0C behavior flags (bits 0-4).
- `wide_struct_init` (0x8F25): gates wide-struct init on scroll_flags bit 1.

**Field updates:**
- IX+0x0C renamed `behavior_flags` in `entity_table.md`.
- 0xE720 added to `scroll_state.md` as `wide_struct_lut_ptr`.

**New KB files:** `entity_clear.md`, `spawn_col_marker.md`,
`handler_type11_base_spawner.md`, `handler_type35_base_eye.md`,
`handler_type80_base_damage.md`. Updated: `entity_jump_table.md`,
`entity_table.md`, `scroll_state.md`.

**Still uncertain:**
- Types 3, 26–29, 37–38, 41–43, 45, 57–68, 72, 83: handlers identified but roles unknown.
- How type-11 slots get populated (what writes type=11 to an entity slot to start a projectile burst).
- 0xE720 exact update mechanism (who writes the wide_struct_lut_ptr).
- Player-tracking entity (type 31/33 at 0x7F84) — confirmed reads player Y (0xE301); full role unclear.
- Type 19 self-transitions to 0x83 (→ type 3 dispatch); transition semantics unclear.

**Next sprint candidates:**
- **0013 — Scroll velocity ramp** (needs user-assisted live debug near a base).
- **0014 — Entity slot allocator** (0x4496): understand how new entities are spawned
  and which types are written to free slots during gameplay.
- **0015 — Player bullet system**: trace type-2 handler (0x7221), confirm 0xE10F/0xE10E
  fire pattern and velocity sources; map the fire key → type-2 spawn path.
