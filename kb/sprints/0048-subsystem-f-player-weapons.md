---
id: "0048"
status: done
range: 0x4cf7-0x4da4,0x7221-0x7747,0x7748-0x778e,0x778f-0x77be
strategy: subsystem_slice
budget_turns: 40
subsystems: [F]
---

# Sprint 0048 — Subsystem F (Player Ship & Weapons): take to fully documented

## Goal

Take subsystem F from ~40% to fully documented (all `confirmed`). The shot system
and the player-input/hit half are already KB'd; the gaps are:

1. The **fire-weapon engine** — switcher (0x7548), per-frame life timer (0x730b),
   the 8 fire-weapon handlers reached through three inline jump tables
   (init 0x7269, update 0x727f, expire 0x74ae), and the fire readout (0x7594).
2. The **player-ship entity handler** (0x75d5 init / 0x7612 per-frame): movement,
   shot spawning, fire spawning, sprite write.
3. The shared **velocity-vector setter** `set_velocity_from_dir` (0x4cf7) —
   currently mis-labelled in CLAUDE.md as a "vertical-collision distance table"
   and stored as a DB block; it is code + a 16-direction velocity table (0x4d65).
4. Data tables: fire-init limits (0x751f), fire-special params (0x752f),
   X-velocity selector (0x7758), shot-rate (0x7761), shot-power (0x778f),
   8-dir delta (0x7748).

## Inputs

- `kb/subsystems/F-player-ship-and-weapons.md`
- `kb/symbols/0x4000-init/{read_player_input,fire_edge_detect,player_hit_handler,wait_fire_or_timeout}.md`
- `kb/symbols/0x4900-hud/player_pos_snapshot.md`
- `kb/symbols/0xE000-gamestate/{fire_num,shot_*,player_x_vel}.md`
- Source: 0x4cf7–0x4da4 (velocity setter), 0x7221–0x77be (weapon/ship engine).
- Helpers: 0x5189 (play_sfx, O), 0x5c2e (inline-table dispatch), 0x4cf7.
- Sprint 0038 (close as part of this slice): 0x730b fire branch.

## Verification plan

`tools/sprint0048_verify.py` — micro-exec / live capture in openMSX:
- Plant `fire_num` (E14B) values, call switcher 0x7548, read back E14D/E14E vs
  table 0x751f.
- Breakpoint each fire-weapon handler during live play with each weapon selected;
  confirm the jump-table dispatch maps fire_num → handler.
- Drive the ship (steer/shoot/fire) live; confirm movement clamps, shot spawn into
  E320 slot table, fire spawn into E380, and the fire readout VRAM write.
- Confirm `set_velocity_from_dir` output (IX+8/9, IX+a/b) for known directions.

## Summary (filled at end)

**Subsystem F → fully documented ✓. 39 live checks passed (32 micro-exec engine +
7 live behaviour).**

### Confirmed (micro-exec / live capture)

| Routine | Evidence |
|---------|----------|
| `set_velocity_from_dir` 0x4cf7 | dir→IX velocity matched `vel_dir_table` for dirs 0/2/4/6/8/12 (e.g. 0→(0,+128), 4→(+128,0)) |
| `fire_select` 0x7548 | all 8 fire_num → E14D/E14E = `fire_init_table[n]`, E14C=0x3c, E14B=n |
| `load_shot_params` 0x7771 | levels 0–5 → E10E/E10D/E10F = `shot_power_table[lvl]` |
| `dispatch_inline_table` 0x5c2e | fire_num → handler via 3 phases (init 0x7269 / update 0x727f / expire 0x74ae) for fire 0/3/4/7 |
| `player_ship_update` 0x7612 | steer right/left/up moved E302/E301; holding fire hit the shot-spawn write 0x76d9 |
| `update_fire_display` 0x7594 | "FIRE " @0x3a59, digit '3' @0x3a5e, ammo " 64" @0x3a7a |

### Corrections

- **CLAUDE.md "0x4CF7–0x4DA5 vertical-collision distance table" was wrong** — it is
  `set_velocity_from_dir` (code, was a DB block) + `dir_angle_thresholds` (0x4d42),
  `dir_remap_table` (0x4d45) and `vel_dir_table` (0x4d65). Disassembled + KB'd; DB
  tracker row removed.
- **0x730B is `fire_life_timer`** (ammo/expiry countdown), not the "fire_type
  branch" hypothesised in sprint 0038 (now closed). Fire-type selection is the
  separate 0x5c2e dispatch.
- The fire readout (FIRE label/number/ammo) is `update_fire_display` at **0x7594**
  (subsystem F), distinct from the 0x4DA5 `pause_handler` that once carried that name.

### New symbols / data / source

- 11 new symbol files (0x7000-weapons/: shot_handler, fire_weapon_handler,
  fire_life_timer, fire_dec_ammo, fire_reset, fire_select, update_fire_display,
  player_ship_handler, player_ship_update, load_shot_params;
  0x4000-init/set_velocity_from_dir; 0x5000-gameplay/dispatch_inline_table).
- 7 data files + 1 guide (vel_dir_table, fire_init_table, fire2_special_table,
  fire0_dir_table, xvel_table, shot_rate_table, shot_power_table; guide
  fire-weapon-dispatch). `read_player_input` bumped likely→confirmed.
- Source: 0x4cf7–0x4d41 disassembled; ~8 mis-decoded data/jump-table regions
  converted to labelled DB/DW (fire_init_dispatch/fire_update_dispatch/
  fire_expire_dispatch, fire_init_table, fire2_special_table, fire0_dir_table,
  dir8_delta_table, xvel_table, shot_rate_table, shot_power_table, "FIRE "
  inline string, vel_dir_table); 9 routine labels added/renamed. `redisasm verify`
  byte-identical.

### Files

- `kb/subsystems/F-player-ship-and-weapons.md` coverage `done`; `CLAUDE.md` F → done ✓,
  DB tracker row removed, 0038 closed.
- `tools/sprint0048_verify.py`, `tools/sprint0048_live.py`.

`zanackb validate` 0 errors. `redisasm verify` byte-identical.
