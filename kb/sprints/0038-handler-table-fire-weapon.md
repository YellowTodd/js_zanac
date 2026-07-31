---
id: "0038"
status: done
range: 0x71DB-0x71DB,0x71F6-0x71F6,0x730B-0x730B
strategy: forward_from_caller
budget_turns: 15
subsystems: [F, G, C]
---

# Sprint 0038 — Entity handler table helpers and fire-weapon branch

> **Subsystem slice:** primary [[F-player-ship-and-weapons]] (`LAB_730B`
> fire-weapon branch, 0x730B) — close 0038 when the F weapons slice lands. Also
> feeds [[G-enemy-and-spawn-system]] (`0x71F6` spawn-child helper) and
> [[C-entity-framework]] (`0x71DB`, reached via `alloc_entity_slot`).

## Goal

Document three addresses in the 0x71xx–0x73xx handler area that are called by
documented symbols but have no KB entries:

1. **`0x71DB`** — called by `alloc_entity_slot` (0x4496).  The slot allocator
   already calls `0x4496` itself (to find a free slot in 1–4 or 1–21 range).
   This secondary call at 0x71DB suggests it's reached via the entity jump
   table or a type-specific allocator.  The entity jump table at 0x70B7 maps
   type IDs to handler addresses — 0x71DB may be a handler entry or a helper
   called from one.
2. **`0x71F6`** — called by `handler_type46_ground_projectiles`.  Located just
   after the jump-table data block.  Hypothesis: a spawn-child helper that
   allocates a sub-entity slot, sets its type/velocity, and links it.
3. **`LAB_730B`** (0x730B) — called by `handler_type31_stealth_tracker`.  In
   the 0x7221–0x72FF player/shot handler block.  Hypothesis: the `fire_type`
   branch — reads E14B (fire_type 0–7) and selects the fire-weapon variant
   for the type-3 entity spawned by Z or joystick.

## Inputs

- `kb/symbols/0x4000-init/alloc_entity_slot.md` — calls 0x71DB
- `kb/symbols/0x8000-enemy/handler_type46_ground_projectiles.md` — calls 0x71F6
- `kb/symbols/0x8000-enemy/handler_type31_stealth_tracker.md` — calls 0x730B
- `kb/symbols/0x5000-gameplay/title_intro_seq.md` — entity_jump_table at 0x70B7
- `kb/data/entity_table.md` — type IDs and slot assignments
- `kb/guides/keyboard-input.md` — E14B (fire_type) description
- Source lines 3409–3430 (0x71DB–0x71F6 area)
- Source lines 3540–3570 (0x730B area)

## Verification plan

### Step 1 — Identify 0x71DB in context (static)

Read source lines 3400–3435.  Determine whether 0x71DB is:
- A code subroutine (find a preceding label and CALL pattern)
- A jump-table entry (i.e., alloc_entity_slot jumps into the entity type's
  handler, which then calls alloc_entity_slot recursively for a child slot)

Cross-reference the jump table data at 0x70B7 to see which type's handler
lives at or near 0x71DB.

### Step 2 — Decode 0x71F6 (static)

Read source lines 3420–3445 (0x71F6 area).  Map its inputs/outputs and
confirm whether it's an entity-spawn helper or a position-update sub.

### Step 3 — Decode LAB_730B fire_type branch (static)

Read source lines 3540–3580.  Confirm that E14B selects among weapon variants
and identify the table or jump that maps fire_type → entity sub-type.  This
should close the loop from sprint 0032 which deferred this trace.

## Key questions

- Is 0x71DB reached via CALL from `alloc_entity_slot`, or is `alloc_entity_slot`
  called FROM code near 0x71DB (i.e., is 0x71DB the `called_by` host)?
- Does 0x71F6 share any code with `alloc_entity_slot` (0x4496)?
- Does `LAB_730B` read E14B directly, or through a cached copy in a register?

## Expected KB entries

- `kb/symbols/0x4000-init/` or `0x8000-enemy/` — entry for 0x71DB (name TBD)
- `kb/symbols/0x8000-enemy/spawn_child_entity.md` — 0x71F6 (if confirmed)
- `kb/symbols/0x8000-enemy/fire_type_branch.md` — `LAB_730B` (0x730B)

## Summary (filled at end)

**Closed by sprint 0048** (subsystem F slice).

- **0x730B** — the hypothesised "fire_type branch" is in fact [[fire_life_timer]]:
  the per-frame E14C/E14D countdown that expires the active fire weapon to
  [[fire_reset]]. The fire-type *selection* is the separate [[dispatch_inline_table]]
  (0x5c2e) → [[fire-weapon-dispatch]] mechanism, also documented in 0048.
- **0x71DB / 0x71F6** — not part of subsystem F; these remain open as
  G/C entity-helper items (the spawn-child helper called by
  `handler_type46_ground_projectiles`, and the `alloc_entity_slot` secondary
  call). Re-scope under the G slice when it lands.
