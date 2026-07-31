---
letter: G
title: Enemy & Spawn System
coverage: done
status: done
---

# G — Enemy & Spawn System

## Role

Everything that puts hostile objects on screen and runs their behaviour: the
spawn scheduler (timed/positional from the per-stage spawn table and attack
list), the ground-structure and base-encounter controllers, and the individual
enemy *type handlers* dispatched by [[C-entity-framework]]. Spawn rate/aggression
is modulated by [[I-alc-adaptive-difficulty]]. The base encounter ties into
[[D-scroll-and-tile-rendering]] (scroll decel/stop).

## Spawn / encounter control

| Addr | Name | Conf | Notes |
|------|------|------|-------|
| 0xBE76 | `spawn_table` | confirmed (data) | per-stage spawn schedule |
| 0xBE27 | `update_spawn_table_ptr` | confirmed | advance schedule pointer |
| 0xBF2C | `ground_struct_spawn_ctrl` | confirmed | ground-object spawner |
| 0xBF94 | `spawn_type3d_slot` | confirmed | spawn a type-3D slot |
| 0xBFA0 | `sub_bfa0` | confirmed | encounter helper |
| 0xBFAB–0xBFD0 | `inc/dec_encounter_*` | confirmed | encounter counters (6 files) |
| 0xBFD6 | `base_encounter_ctrl` | hypothesis | base open/close/fire cycle |
| 0x71DA | `spawn_col_marker` | confirmed | column spawn marker |
| 0xE780 | `attack_list` | confirmed (data) | active attack/spawn list |

## Enemy type handlers (documented)

| Addr | Name | Type | Sprint |
|------|------|------|--------|
| 0x7826 | `handler_type4_box` | 4–6 | 0049 |
| 0x791D | `handler_type7_umber` | 7–9 | 0049 |
| 0x7A2A | `handler_type10_duster` | 10 | 0049 |
| 0x7A67 | `base_spawner_active` | 69 | 0049 |
| 0x7AD4 | `handler_type11_base_spawner` | 11 | — |
| 0x7B07 | `handler_type12_teruzo` | 12–15 | 0049 |
| 0x7BEB | `handler_type16_luster` | 16/17/18 | 0049 |
| 0x7D0F | `handler_type22_veybar` | 22–23 | 0050 |
| 0x7DB4 | `handler_type24_veybar_fast` | 24–25 | 0050 |
| 0x7DE2 | `handler_type26_edge_swooper_a` | 26–27 | 0050 |
| 0x7E78 | `handler_type28_edge_swooper_b` | 28–29 | 0050 |
| 0x7E9C | `handler_type30_ground_swooper` | 30/32 | 0050 |
| 0x7F73 | `handler_type31_stealth_tracker` | 31/33/34/65/66 | — |
| 0x77A1 | `handler_type68_proto_box` | 68 | 0051 |
| 0x8094 | `handler_type46_ground_projectiles` | 46–55 | — |
| 0x816D | `fire_ground_projectile` | (sub) | 0051 |
| 0x819D | `handler_type56_sig_single` | 56/59 | 0051 |
| 0x81D1 | `handler_type57_paired_descender` | 57/58 | 0051 |
| 0x8279 | `handler_type64_proto_structure` | 64 | 0051 |
| 0x82D0 | `handler_type44_ground_structure` | 44 | 0051 |
| 0x8296 | `handler_type36_flashing` | 36 | 0050 |
| 0x8302 | `handler_type61_large_descender` | 61 | 0051 |
| 0x839F | `handler_type67_med_circle` | 67 | 0051 |
| 0x8446 | `handler_type35_projectile` | 35 | — |
| 0x84DD | `handler_type37_lead_bullet` | 37 | 0050 |
| 0x8501 | `handler_type38_burst_fragment` | 38 | 0050 |
| 0x852F | `handler_type41_pair_fragment` | 41 | 0051 |
| 0x85CC | `handler_type42_proto_bullet` | 42/43 | 0051 |
| 0x85EE | `handler_type45_light_bar_var` | 45 | 0051 |
| 0x8635 | `handler_type21_light_bar` | 21 | 0050 |
| 0x8668 | `handler_type20_lead_homing` | 20 | 0050 |
| 0x8709 | `handler_type62_invisible_riser` | 62 | 0051 |
| 0x87AB | `handler_type70_wide_structure` | 70–71/81–82/87–89 | 0052/0059 (the shootable **idol**; reads 0xE720 idol table → orb warp dest) |
| 0x8983 | `handler_type72_base_core` | 72 | 0052/0059 (the **orb**: yellow=kill-all, black=**warp**; see [[idol-warp-orbs]]) |
| 0x8A26 | `explode_enemies` | — | — |
| 0x8A5A | `handler_type73_base_segment` | 73–79 | 0052 |
| 0x8E14 | `handler_type80_base_damage` | 80 | — |
| 0x8E3A | `handler_type83_black_shadow` | 83 | 0052 |
| 0x8EB7 | `handler_type84_wide_variant` | 84–86 | 0052 |
| 0x8F25 | `wide_struct_init` | (sub) | 0052 |

> Note: **type 19 (0x74a4) is NOT an enemy** — it is the fire-weapon expire path
> (subsystem F); excluded from G's handler count.

## Group-by-group roadmap (~12 types per sprint)

| Sprint | Group | Types | Status |
|--------|-------|-------|--------|
| 0049 | 1 — early airborne | 4–18 (box/umber/duster/teruzo/luster) + 69 | **done ✓** |
| 0050 | 2 — homing/swoopers/bullets | 20–30, 32, 36–38 | **done ✓** |
| 0051 | 3 — fragments/structures/descenders | 41–45, 56–59, 61–62, 64, 67–68 | **done ✓** |
| 0052 | 4 — wide structures / bases (DB disasm) | 70–89 + spawn-ctrl finalize | **done ✓** |

## State

`spawn_subtable_max` (0xE136), `spawn_variant_ctr` (0xE149),
`ground_spawn_countdown` (0xE124), `sprite_count` (0xE11F).

## Gaps / open questions

**All enemy type-handlers documented (groups 1–4, sprints 0049–0052); subsystem
G fully documented.** Residual items, none blocking:

- The 0x8983 / 0x8a5a handler blocks are now disassembled code (sprint 0052,
  ROM byte-identical); `base_encounter_ctrl` (0xbfd6) corrected to the HUD readout.
- The 7 byte-neutral mis-decoded data tables (0x77ea, 0x7808, 0x79b7, 0x7af7,
  0x7b7b, 0x7e68/0x7e70) are now labelled `DB` blocks (sprint 0053, via the new
  `redisasm data` command; ROM byte-identical). See [[db-sections-with-code]].
- Types 60 (player death explosion) and 63 (player respawn) are documented under
  C/F, not G.

## Sprints

Done: 0006, 0011, 0012, 0013, 0022, 0025, 0026, 0031, 0039 (both parts via
0049/0051), 0049 (group 1), 0050 (group 2), 0051 (group 3), 0052 (group 4 → G done).
**Open — secondary feeders:** 0038 (`0x71F6` spawn-child helper), 0036 (delivers
the 0x4CF7 velocity-from-table setter used by `handler_type31`).
