---
id: "0044"
status: done
range: 0x445F-0x4490,0x44D4-0x455F,0x4898-0x48A8,0x4C8B-0x4CF6,0x716B-0x71C4
strategy: subsystem_slice
budget_turns: 26
subsystems: [C]
---

# Sprint 0044 — Subsystem C (Entity Framework): confirm all routines

## Goal

Take subsystem C to fully documented (all `confirmed`). Five routines were
`likely` — `entity_dispatch`, `collision_dispatch`, `collision_response`,
`entity_update`, `player_pos_snapshot` — and the collision-result table at
0x716B was referenced but not a KB entry. Execution-verify the routines and
document + DB-convert the table.

## Inputs

- `kb/subsystems/C-entity-framework.md`
- `kb/symbols/0x4000-init/{entity_dispatch,collision_dispatch,collision_response,entity_update}.md`
- `kb/symbols/0x4900-hud/player_pos_snapshot.md`
- `kb/data/entity_jump_table.md` (already fully enumerated + confirmed in 0012)
- Source: dispatcher 0x445F–0x4490, collision 0x44D4–0x455F, 0x4898–0x48A8,
  player snapshot 0x4C8B–0x4CF6, table 0x716B–0x71C4.

## Verification plan

`tools/sprint0044_verify.py` — openMSX, live gameplay (no PC/SP hijack, game
stays healthy). Breakpoint hit-counts + capture actions; ROM cross-checks read
from `source/zanac.rom`.

## Summary (filled at end)

**All 9 checks passed; subsystem C → fully documented ✓.**

### Confirmed (likely → confirmed)

| Addr | Routine | Evidence |
|------|---------|----------|
| 0x445F | `entity_dispatch` | ~32 calls/0.5 s; captured handler at `JP HL` (0x4486) for t1/t39/t44/t61 all == `*(0x70B7+(type&0x7F)*2)`; 0xE11F = 0xE122 low at loop end |
| 0x4898 | `entity_update` | ~88/0.5 s; type-10 duster (bflags 0x13, bit 4) drove X-homing 0x496B 252×, Y-homing 0x4942 0× |
| 0x44D4 | `collision_dispatch` | ~125/0.5 s; carry path leads into 0x453E on shot-vs-enemy |
| 0x453E | `collision_response` | captured in/out types: t44→35, t4→35, t1→60, t2→40 — each == `tbl[type]` |
| 0x4C8B | `player_pos_snapshot` | at 0x4C9D: 0xE129==0xE301, 0xE12A==0xE302 every hit |

### Key finding — dispatcher drops bit 7

`entity_dispatch` does `ADD A,A` on the **full** type byte (no mask). Active
entities carry bit 7, which shifts out of the 8-bit accumulator, so the index is
`(type*2)&0xFF` ≡ `(type&0x7F)*2`. Handler = `*(0x70B7 + (type&0x7F)*2)`. This is
why `entity_jump_table` uses virtual base 0x70B7 and masked indexing.

### New data entry + DB conversion

`death_transition_table` (0x716B–0x71C4, 90 bytes, `confirmed`). `type & 0x7F` →
post-collision type, applied to both parties by `collision_response`. Five death
classes: 35 = enemy explosion (most enemies), 40 = instant despawn (shots/bullets),
80 = base damage (ground structures), 60 = player death explosion (player→60), 19
(fire-weapon-0). The region was mis-disassembled as code (NOP/INC HL…); converted
to a labeled `DB` block (`death_transition_table:`) at lines 3232–3311, decode
boundary clean (code resumes at 0x71C5 = `random_x_pos`). `redisasm verify`
byte-identical.

### Files

- 5 symbol files `likely`→`confirmed` with live-confirmation notes, `sprint: 0044`.
- New `kb/data/death_transition_table.md`; `collision_response.md` links it.
- Source: 0x716B–0x71C4 → DB block + label.
- `C-entity-framework.md`: coverage `done`, gaps cleared, snapshot + table added.
- `CLAUDE.md` coverage table C → done ✓.
- `tools/sprint0044_verify.py`.

`zanackb validate` 0 errors. `redisasm verify` byte-identical.
