---
name: fire-weapon-dispatch
description: "The 3-phase fire-weapon dispatch — inline word-tables at 0x7269 (init), 0x727f (update), 0x74ae (expire), each 8 entries keyed on fire_num, consumed by dispatch_inline_table (0x5c2e). Maps fire_num 0-7 to its per-weapon handlers."
kind: guide
confidence: confirmed
sprint: "0048"
tags: [fire, weapon, dispatch, jump-table]
---

# fire-weapon-dispatch (3-phase fire-weapon dispatch)

The three inline word-tables live **inside** [[fire_weapon_handler]]'s code span
(0x7269/0x727f) and the expiry path (0x74ae); they are documented here as a guide
rather than as standalone data entries to avoid range overlap with the handler.

## Summary

Three inline word-tables, each 8 entries indexed by `fire_num` (E14B, 0-7),
consumed by the [[dispatch_inline_table]] helper (0x5c2e). They select the
handler for the active fire weapon at three life-cycle phases:

- **`fire_init_dispatch`** (0x7269) — first-frame spawn/init, reached from
  [[fire_weapon_handler]] (0x7253) once per fire-weapon entity.
- **`fire_update_dispatch`** (0x727f) — per-frame update, reached from
  [[fire_weapon_handler]] on subsequent frames.
- **`fire_expire_dispatch`** (0x74ae) — expiry/cleanup, reached when the timer
  ([[fire_life_timer]]) runs the weapon out (entry at 0x74a4).

## Per-weapon handlers

| fire_num | init (0x7269) | update (0x727f) | expire (0x74ae) |
|----------|------|------|------|
| 0 | 0x72b3 | 0x72de | 0x74be |
| 1 | 0x72a8 | 0x72ea | 0x72ea |
| 2 | 0x729d | 0x72f5 | 0x74c1 |
| 3 | 0x7331 | 0x735d | 0x735d |
| 4 | 0x73ce | 0x7439 | 0x74e2 |
| 5 | 0x73c8 | 0x7464 | 0x7464 |
| 6 | 0x73ce | 0x7494 | 0x7511 |
| 7 | 0x728f | 0x7306 | 0x7306 |

Notes from static reading (the per-weapon gameplay identities, e.g. which is the
field / wave / shield weapon, are not individually named here):
fire 4 and 6 share the init handler 0x73ce (split at 0x73e5 on E14B−5).
**Correction (2026-07-30):** the earlier note here tied [[fire0_dir_table]]
(0x7321) to fire 0 - it belongs to **fire 7** (0x728F loads `HL,0x7321`);
fire 0's init (0x72B3) aims through [[xvel_table]] (`LD HL,0x7758`). Both
feed the same common spawn setup at 0x72BC, whose aim path indexes the
table by the steering selector stored at +0x1A.

## Confirmed (sprint 0048)

Planting each `fire_num` and running the dispatcher from the three call sites
(0x7263 / 0x7279 / 0x74a8) landed on exactly the tabulated handler for tested
indices 0/3/4/7 across all three phases. `tools/sprint0048_verify.py`.
