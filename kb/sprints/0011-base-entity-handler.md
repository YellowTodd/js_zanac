---
id: "0011"
status: done
range: 0x70B9-0x71B7
strategy: callgraph_leaf
budget_turns: 35
---

# Sprint 0011 — Base entity handler & 0xE71E spawn path

## Goal

1. Identify which entity type maps to the handler at 0xBFA0 (seen in sprint 0010
   with `RES 0,(IX+0x25)` and `LD (HL), 0x44`).
2. Find who reads 0xE71E (base attack-list pointer) and how type-11 slots
   get populated to start projectile bursts.
3. Confirm the full base-encounter spawn path end-to-end.

## Inputs

- `kb/data/entity_jump_table.md` — table covered types 0–99; need 100–127
- `kb/symbols/0x8000-enemy/handler_type11_base_spawner.md`
- `kb/data/scroll_state.md` — 0xE71E is in scroll_state area

## Verification plan

- Extend jump table read to types 100–127.
- Breakpoint at 0xBFA0 during base encounter; read IX to identify calling type.
- Write-watchpoint on first free slot in entity table during base approach to
  catch what writes type 11.

## Summary (filled at end)

**The "base entity handler" premise was wrong.** The base is not a single entity type
— it is a composition of the scroll engine, multiple entity types, and main-loop code.

**Key finding — `ground_struct_spawn_ctrl` (0xBF2C):**
Called from the main loop at 0x4082 every frame. Sets `IX = 0xE100` (game-state
block), reads a ROM spawn table via pointer at 0xE133–0xE134, and writes entity
type bytes directly into free entity slots via `alloc_entity_slot` (0x4496). The
spawn table observed at 0xBECF = `[44,44,56,56,44,12,10,13,…,11,…]` — this IS
the level entity sequence. Type 11 (base spawner) appears in this table, so base
projectile bursts are triggered by the scroll engine advancing through the level.

**0xBFA0 is a helper**, not an entity handler: it immediately allocates a slot and
writes type 0x44 when `E125 bit0` is set (the "spawn ground structure NOW" trigger).

**0xE71E write path confirmed:** write-watchpoint showed writers at 0x95FF and 0x9631
— both inside `place_tile_group`'s source range. The base attack list at 0xE780
stores RAM tile addresses written when a base tile group is processed.

**0xE100 game-state block decoded** (not player sprite data): 80+ byte structure
holding spawn_trigger (0xE125), stream_slot_ctr (0xE126), spawn_ctrl (0xE12D),
spawn_pos (0xE12E/0xE12F), spawn_table_ptr (0xE133), spawn_timer (0xE137/0xE138),
and spawn_event_ctr (0xE142). Many fields overlap existing 0xE000-gamestate entries
(score, lives, fire_num) confirming the block spans the full 0xE100–0xE14F range.

**New KB files:** `ground_struct_spawn_ctrl.md`, `game_state_block.md`.
**Updated:** `scroll_state.md` (0xE71E documented as base_attack_list_ptr).

**Still uncertain:**
- `0xBE27`: scroll-position update routine called from 0xBF2C; uses 0xBE7C lookup table.
- `0xE133` spawn table pointer source: what writes 0xBECF (or equivalent ROM address) there?
- Exactly how `E125 bit0` gets set (0xE125 write-watchpoint fired 0 times in this session).
- The attack list reader: who reads from 0xE780 to actually fire projectiles at the player?

**Next sprint candidates:**
- **0013 — Scroll velocity ramp** (user-assisted, approach a base).
- **0015 — Player bullet system** (fully static).
- **0016 — Spawn table source**: trace what writes 0xE133 and how the level map
  advances the spawn table pointer.
