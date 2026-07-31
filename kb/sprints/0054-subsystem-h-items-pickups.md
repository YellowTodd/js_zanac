---
id: "0054"
status: done
range: 0x7878-0x7903,0x8e89-0x8eac
strategy: subsystem_slice
budget_turns: 25
subsystems: [H]
---

# Sprint 0054 — Subsystem H (Items & Pickups): take to fully documented

## Goal

Document the collectible economy (boxes, power chips, fire-weapon upgrades),
which is implemented entirely as G entity handlers + F state effects.

## Inputs

- [[handler_type4_box]], [[handler_type68_proto_box]], [[proto_box_type_table]],
  [[handler_type83_black_shadow]] (all from G slices 0049/0051/0052).
- F: [[load_shot_params]], [[shot_power_table]], [[fire_select]].
- `collision_response` 0x453E, `death_transition_table` 0x716B (C).

## Verification

`tools/sprint0054_verify.py` — micro-exec in openMSX (halt CPU, set PC, step).

## Summary

**Subsystem H → fully documented ✓. 7/7 micro-exec checks.**

### Confirmed (live micro-exec)

| Fact | Evidence |
|------|----------|
| type 63 handler | jump_table[63] = 0x78AF |
| box drop = box type | 0x7878 with +0x18=4/5/6 → entity type 0x26 / 0x84(unchanged) / 0xBF |
| power chip applies | 0x78D7 with shot_level 3 → 4, `shot_power_table[4]` reloaded into E10D/E/F (`020428`→`020a30`) |
| fire-weapon grant | black-shadow tail 0x8EA9 with +0x1c=5 → enters `fire_select` with A=5 |

### Mechanics

- **Box drop table = box type.** `collision_response` saves the box's type to
  +0x18 on the first hit; the death branch (0x7878) reads it: **5→nothing,
  4→three bullets (3× type 38), 6→power chip (type 63 = 0xBF)**. The box-type mix
  (drop odds) is set at spawn by [[proto_box_type_table]].
- **Power chip** = type 63 ([[handler_type63_power_chip]], 0x78af): float →
  on contact `shot_level`++ → `load_shot_params` → HUD; maxed → bonus + restart fire.
- **Fire-weapon upgrade** = black shadow (type 83, [[handler_type83_black_shadow]]):
  destroy → `fire_select(+0x1c)`; `+0x1c` is the weapon number (0–7) and colour index.

### Corrections

- **Type 63 was mislabelled "player-respawn handler" (hypothesis) — it is the
  power chip.** Renamed → [[handler_type63_power_chip]]; `entity_jump_table`
  updated confirmed.

### New / changed

- New symbol [[handler_type63_power_chip]]; H overview stub→done;
  `handler_type4_box` (drop table), `handler_type83_black_shadow` (fire grant) and
  `entity_jump_table` (type 63) updated. `tools/sprint0054_verify.py`.

`zanackb validate` 0 errors. No `source/zanac.asm` change.
