---
id: "0013"
status: done
range: 0xE300-0xE63F
strategy: live_debug
budget_turns: 25
---

# Sprint 0013 — Entity type IDs → sprite pattern mapping

## Goal

Map every active entity type to its SAT pattern byte (+0x03) and color byte
(+0x04), then cross-reference with the sprite-names table to assign names.

Key constraint: many types share the same pattern but differ only in color.

## Inputs

- `kb/data/entity_table.md` — slot layout, type byte semantics
- `kb/data/entity_jump_table.md` — handler-level notes per type
- `kb/data/gfx_sprite_patterns.md` — sprite pattern names from StrategWiki
- openMSX breakpoint at entity_dispatch (0x445F)

## Verification plan

Break at entity_dispatch each frame; dump slots 0–25 showing type, pattern,
color; correlate with visible sprites. Repeat with varied enemy populations.

## Summary (filled at end)

20-frame live capture at entity_dispatch (0x445F) combined with static handler
disassembly. New KB file: `kb/features/entity-sprite-mapping.md`.

**Confirmed live** (type, pattern, sprite name):
- Type 1 → pat 14 (player_ship), color 0x81/0x8F (alternates during invincibility)
- Type 2 → pat 10 (fire_single), color 0x8F — player bullet at weapon 0
- Type 3 → pat 9 (large_circle), colors 0x80–0x8F cycling — colorful enemy bullet
- Type 5 → pat 53 (box) after countdown, color 0x8F — floating box
- Type 6 → countdown in SAT_NAME (0x20 frames), then box
- Type 35 → pat 7/8/9/16 (lead/med_circle/lg_circle/plane) — **corrected from sprint 0012**; multi-pattern projectile, NOT base eye animator
- Type 39 → pat 17/54 (plane_shadow/box_sh), invisible (Y=0,X=0) — shadow-sprite dual use
- Type 44 → pat 16 (plane), color 0x83 — ground structure
- Type 56 → pat 28 (sig_single), colors 0x86↔0x8F flashing — falling pickup/missile
- Type 69 → pat 7 (lead), color 0x00 — base projectile, initially transparent

**Inferred from static init code:**
- Types 7/8/9 → pat 55 (umber_A) with shadow pat 57
- Type 10 → pat 22 (duster)
- Types 16/17 → pat 29 (luster_A)
- Types 20/21 → pat 7/6 (lead/light_bar)
- Types 22–25 → pat 33 (veybar_A) with shadow pat 38; colors 0x83 vs 0x89
- Type 82/87 → pat 9 (large_circle) — wide ground structure

**Key finding — shadow-sprite duality:**
`spawn_col_marker` (0x71DA) leaves HL pointing to the new marker slot's +0x03
(pattern byte). The calling handler immediately writes the shadow sprite's
SAT_NAME there. The parent entity's running code repositions the marker via
IY = child slot. Column markers (type 39) are therefore BOTH occupancy trackers
(for check_col_clear) AND rendered shadow sprites.

**Correction:** `handler_type35_base_eye.md` renamed to `handler_type35_projectile.md`;
confidence demoted from confirmed → likely; summary corrected.

**Still unknown:**
- Types 12–15 (subtable at 0x7B63 entries 12-15 are jump addresses 0x7B83/98/AE/CC; patterns in sub-handlers)
- Types 18, 26–34, 36–38, 41–55, 57–67, 70–81, 83–86, 88–89

**Next sprint candidates:**
- **0014b — Types 12–15 live capture**: start game and play until many different
  enemies on screen; run same capture script.
- **0015 — Player bullet system**: trace type-2 handler for weapons 1–7 patterns.
- **0016 — Spawn table source**: what writes 0xE133 to advance the level sequence.
