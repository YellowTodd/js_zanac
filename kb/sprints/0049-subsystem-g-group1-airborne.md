---
id: "0049"
status: done
range: 0x7800-0x7d0e
strategy: subsystem_slice
budget_turns: 40
subsystems: [G]
---

# Sprint 0049 — Subsystem G group 1 (early airborne enemies, types 4–18)

## Goal

First of the planned ~12-types-per-sprint slices that take subsystem G to fully
documented. This group covers the contiguous handler block **0x7826–0x7d0e**
(plus the type-19 correction and the base-spawner active state at 0x7a67):

| Types | Handler | Name | Notes |
|-------|---------|------|-------|
| 4,5,6 | 0x7826 | `handler_type4_box` | box enemy: countdown→spawn col-marker + reveal |
| 7,8,9 | 0x791d | `handler_type7_umber` | umber cluster, 3 init entries (0x791d/0x79be/0x79fb) |
| 10    | 0x7a2a | `handler_type10_duster` | duster: Y+X+X-homing |
| 12–15 | 0x7b07 | `handler_type12_teruzo` | teruzo: per-type spawn+motion tables 0x7b7b |
| 16    | 0x7beb | `handler_type16_luster` | luster: straight fall, spawns col-marker |
| 17    | 0x7c8a | `handler_type17_luster_homing` | luster, Y+X+X-homing variant |
| 18    | 0x7cb3 | `handler_type18_luster_left` | luster, leftward homing variant |
| 69    | 0x7a67 | `base_spawner_active` | base-spawner active state (closes 0039 part 1) |

Type 11 (0x7ad4) is already documented. **Type 19 (0x74a4) is NOT an enemy** —
it is the fire-weapon expire path (reads `fire_num` 0xE14B, dispatches
`fire_expire_dispatch`); reassign to subsystem F and drop from G's handler count.

## Embedded data tables to convert (mis-decoded DB)

Each table sits immediately before a handler that begins `DD CB 00 7E`
(`BIT 7,(IX+0)`); the greedy decode absorbs the leading `DD`, shifting the
handler entry by one byte. Convert to labelled DB and re-decode the entry:

- **0x7800–0x7825** `box_param_table` — 8 countdown bytes + box reveal pattern data (before 0x7826)
- **0x79b7–0x79bd** `umber_color_table` — burst color list (before 0x79be)
- **0x7af7–0x7b06** `base_spawner_pos_table` — type-11 X-position table (before 0x7b07)
- **0x7b7b–0x7bea** `teruzo_motion_tables` — 4-entry LE pointer table + 4 per-type Y/X/color + 16-dir motion lists (before 0x7beb)

## Inputs

- `kb/data/entity_jump_table.md` (confirmed per-type behaviour summary)
- `kb/symbols/0x8000-enemy/{handler_type11_base_spawner,handler_type31_stealth_tracker,spawn_col_marker}.md`
- `kb/subsystems/{G-enemy-and-spawn-system,C-entity-framework}.md`
- Source: 0x7800–0x7d0e. Helpers: 0x71da (spawn_col_marker), 0x71c5 (random_x_pos),
  0x71f6 (spawn-child helper), 0x4cf7 (set_velocity_from_dir), 0x8ddb (spawn_entity),
  0x4496 (find_free_slot), 0x4898 (entity_update), 0x44ba (entity_post).
- Sprint 0039 (close part 1: 0x7a67 base-spawner active).

## Verification plan

`tools/sprint0049_verify.py` — live capture in openMSX:
- Spawn each type via the entity pool (write type byte + activate), step frames,
  read back IX fields (+0x03 sat_name, +0x04 color, +0x09 vy, +0x0c bflags) and
  confirm against decode.
- Box: confirm +0x03 countdown → reveal pattern 0xD4 + col-marker spawn.
- Umber: confirm burst spawns (type 38 ×7 / type 41 ×2 / type 20 timer).
- Teruzo: confirm per-type spawn Y/X/color from `teruzo_motion_tables`.
- `redisasm verify` byte-identical after the 4 DB conversions.

## Summary (filled at end)

**Subsystem G group 1 (types 4–18) done ✓. 8/8 live checks passed** (3 ROM data
tables + 5 handler-init captures via slot injection, `tools/sprint0049_verify.py`).

### Confirmed (live capture / ROM read)

| Item | Evidence |
|------|----------|
| `handler_type4_box` (4–6) | injected, +0x03 countdown→reveal sat=0xD4, hp(+0x19)=5, vy_frac(+0x08)=0xC0 |
| `handler_type7_umber` (7–9) | sat=0xDC, X=120, bflags=0x09 (Y+Yhom), y_accel(+0x15)=0x10; vy starts 3 then homing reduces |
| `handler_type10_duster` (10) | sat=0x58, col=0x89, bflags=0x13, vy=3 |
| `handler_type12_teruzo` (12–15) | sat=0x60, bflags=0x03, spawned corner (Y=112,col=0x8A) = block 0x7b83; X drifts |
| `handler_type16_luster` (16/17/18) | sat=0x74, col=0x8E, vy=2 |
| `base_spawner_active` (0x7a67) | ROM-byte hand-decode; emits `count` of `enemy_type` from `base_spawner_spawn_table`, bounces X, retires |
| `base_spawner_spawn_table` (0x7af7) | 8 (type,count) pairs read from ROM = expected bytes |
| `teruzo_motion_tables` (0x7b7b) | 4 LE ptrs → 0x7b83/98/ae/cc; block Y/X/colours read & matched the four corners |
| `umber_burst_param_table` (0x79b7) | 7 bytes read = `04 05 02 07 03 06 01` |

### Corrections

- **Type 19 (0x74a4) is not an enemy** — it is the fire-weapon expire path
  (reads `fire_num` 0xE14B, dispatches `fire_expire_dispatch`), subsystem F.
  Removed from G's handler count.
- `base_spawner_pos_table` (the name guessed pre-sprint) is actually
  `base_spawner_spawn_table` — **(enemy_type, count)** pairs, not positions.

### New symbols / data

- 6 handler files (0x8000-enemy/: handler_type4_box, handler_type7_umber,
  handler_type10_duster, base_spawner_active, handler_type12_teruzo,
  handler_type16_luster) covering types 4–18 + 69.
- 3 data files (kb/data/: base_spawner_spawn_table, teruzo_motion_tables,
  umber_burst_param_table).
- `tools/sprint0049_verify.py`.
- Closes sprint 0039 part 1 (`LAB_7A67` → `base_spawner_active`).

### Deferred

- **Source relabel** of the 4 byte-neutral mis-decoded data tables (0x7800,
  0x79b7, 0x7af7, 0x7b7b). They round-trip to identical ROM (verify passes), but
  are shown as instructions and shift the following handler's entry by one
  (`DD` absorption). `redisasm patch` only converts DB→code, not the reverse;
  documented in `db-sections-with-code.md` for a later reverse-direction pass.

`zanackb validate` 0 errors. `source/zanac.asm` unchanged (no DB conversion this
sprint).
