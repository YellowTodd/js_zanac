---
id: "0051"
status: done
range: 0x77a1-0x77e9,0x816d-0x8188,0x819d-0x839e,0x852f-0x8634,0x8709-0x8749
strategy: subsystem_slice
budget_turns: 40
subsystems: [G]
---

# Sprint 0051 — Subsystem G group 3 (fragments / structures / descenders)

## Goal

Third ~12-types slice + close sprint 0039 part 2. Types 39/40/46–55 already done;
60/63 are F/C. This group: 41–45, 56–59, 61–62, 64, 67–68, plus
`fire_ground_projectile` (0x816d).

| Type(s) | Handler |
|---------|---------|
| 41 | `handler_type41_pair_fragment` |
| 42–43 | `handler_type42_proto_bullet` (scatter converters → 37/38) |
| 44 | `handler_type44_ground_structure` |
| 45 | `handler_type45_light_bar_var` |
| 56, 59 | `handler_type56_sig_single` |
| 57–58 | `handler_type57_paired_descender` |
| 61 | `handler_type61_large_descender` |
| 62 | `handler_type62_invisible_riser` |
| 64 | `handler_type64_proto_structure` |
| 67 | `handler_type67_med_circle` |
| 68 | `handler_type68_proto_box` |
| — | `fire_ground_projectile` (0x816d, closes 0039) |

## Verification plan

`tools/sprint0051_verify.py` — inject each type, check init fields; confirm
tables from ROM.

## Summary

**Group 3 done ✓. 15/15 live checks** (2 ROM tables + 13 handler injections,
`tools/sprint0051_verify.py`).

### Confirmed (live capture)

| Handler | Evidence |
|---------|----------|
| `handler_type41_pair_fragment` (41) | sat=1C bflags=03; two-dir curve via +0x1a/+0x1b |
| `handler_type42_proto_bullet` (42/43) | type→0xA5 / 0xA6 (active 37/38) + velocity scatter |
| `handler_type44_ground_structure` (44) | sat=40 col=83 bflags=03; aims via snapshot |
| `handler_type45_light_bar_var` (45) | col=8F bflags=03 hp=3; active sprite=0x20 |
| `handler_type56_sig_single` (56/59) | sat=70 bflags=03 +0x1f=20; colour XOR 0x09 |
| `handler_type57_paired_descender` (57/58) | sat=6C/68; → type 59 on fire |
| `handler_type61_large_descender` (61) | sat=F8 vy=2; colour from 0x8eaf cycle |
| `handler_type62_invisible_riser` (62) | sat=00 col=87 vy=FF; 16-frame trigger |
| `handler_type64_proto_structure` (64) | converts via spawn_table read @0xbecc |
| `handler_type67_med_circle` (67) | sat=20 col=86 hp=5; +0x1b/1c = 0x1e78 lifetime |
| `fire_ground_projectile` (0x816d) | muzzle 0x4c + spawns child type +0x1f |

### Corrections

- **Type 68 proto-box** is a **3-box-cluster spawner** (tables 0x77ea / 0x7808),
  not a single type-4 converter. The 0x7800–0x7807 bytes are the tail of
  [[proto_box_type_table]] — supersedes group-1's `data_7800` placeholder.
- **Type 64 proto-structure** is a **table-driven** type selector reading
  [[spawn_table]] @0xbecc by difficulty, not a fixed type-44 converter.
- **Type 67 med_circle** +0x1b/1c is a 16-bit **lifetime (0x1e78)**, not the
  "child_ptr 0x1e5e" guessed in sprint 0013.

### New symbols / data

- 12 handler files + `fire_ground_projectile` (0x8000-enemy/).
- 3 data files: [[proto_box_type_table]], [[proto_box_sat_table]],
  [[large_descender_color_table]].
- `tools/sprint0051_verify.py`. Closes sprint **0039** (both parts).

`zanackb validate` 0 errors. `source/zanac.asm` unchanged.
