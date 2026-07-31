---
id: "0052"
status: done
range: 0x87ab-0x8947,0x8983-0x8a25,0x8a5a-0x8bc9,0x8e3a-0x8f5d
strategy: subsystem_slice
budget_turns: 40
subsystems: [G]
---

# Sprint 0052 — Subsystem G group 4 (wide structures & bases, types 70–89)

## Goal

Final G slice: the base / wide-structure handlers, the two raw DB handler blocks
(0x8983, 0x8a5a), and the spawn/encounter-control clean-up. Takes G to fully
documented.

| Types | Handler |
|-------|---------|
| 70–71, 81–82, 87–89 | `handler_type70_wide_structure` |
| 72 | `handler_type72_base_core` (DB→code) |
| 73–79 | `handler_type73_base_segment` (DB→code) |
| 83 | `handler_type83_black_shadow` |
| 84–86 | `handler_type84_wide_variant` |
| — | `wide_struct_init` (0x8f25) |

## Summary

**Group 4 done ✓ → subsystem G fully documented. 7/7 live checks**
(`tools/sprint0052_verify.py`); both DB blocks disassembled **ROM byte-identical**.

### DB disassembly (redisasm patch, ROM byte-identical)

- **0x8983–0x8a15** → `handler_type72_base_core` code; 0x8a16–0x8a25 kept as DB
  ([[base_core_anim]]).
- **0x8a5a–0x8bc9** → `handler_type73_base_segment` code (368 bytes).
- Labels `LAB_ram_8983` / `LAB_ram_8a5a` inserted.

### Confirmed (live capture)

| Handler | Evidence |
|---------|----------|
| `handler_type72_base_core` (72) | +0x11=16 (anim ptr) bflags=05 vy=FF; on death sets round flag e102 bit5 |
| `handler_type73_base_segment` (73–79) | gated on e700 bit1 + e150 bit1; sat/HP from [[base_segment_table]] (73→sat20 hp40) |
| `handler_type83_black_shadow` (83) | type→0xD3 vy=FF vyf=E0 bflags=01; reinits player on death |
| `handler_type70_wide_structure` (70) | gate + sat=0x24 structure tile |
| `handler_type84_wide_variant` (84–86) | sat=24 +0x1c=03; wave spawner (types 21/38) |
| `base_segment_table` / `base_core_anim` | ROM bytes matched |

### Corrections

- **Type 72 is the base CORE / objective** (sets round-clear flag e102 bit5 on
  death), not merely "slow-rise animated".
- **Types 73–79 are base SEGMENTS** parameterised by [[base_segment_table]]
  (0x8df1), gated by **0xe150 bit1 = base-active** (confirmed) after 0xe700 bit1
  scroll-in.
- **0xbfd6 `base_encounter_ctrl` is a misnomer** — it is the encounter-counter
  **HUD hex readout** (render_hex_byte ×3 of e12e/e132/e130), not the base
  open/close/fire controller. Upgraded hypothesis→confirmed with the corrected
  description.

### New symbols / data

- 6 handler files (0x8000-enemy/) + 2 data files ([[base_core_anim]],
  [[base_segment_table]]). `base_encounter_ctrl` corrected. `tools/sprint0052_verify.py`.
- `source/zanac.asm`: 2 DB blocks disassembled (515 bytes), 2 labels added;
  `redisasm verify` byte-identical.

`zanackb validate` 0 errors.
